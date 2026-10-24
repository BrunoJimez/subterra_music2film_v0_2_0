from __future__ import annotations

import json
import math
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from .config import RenderConfig
from .filters import apply_filter
from .media import MediaPool


class FeatureStream:
    def __init__(self, npz_path: str | Path):
        d = np.load(npz_path)
        self.times = d["times"]
        self.channels = {k: d[k] for k in d.files if k not in {"times", "beat_times", "section_bounds"}}
        self.beat_times = d["beat_times"]
        self.section_bounds = d["section_bounds"]

    def value(self, name: str, t: float) -> float:
        arr = self.channels.get(name)
        if arr is None or len(arr) == 0:
            return 0.0
        return float(np.interp(t, self.times, arr))

    def beat_pulse(self, t: float, decay: float = 9.0) -> float:
        if len(self.beat_times) == 0:
            return 0.0
        i = np.searchsorted(self.beat_times, t, side="right") - 1
        if i < 0:
            return 0.0
        return float(math.exp(-max(0.0, t - float(self.beat_times[i])) * decay))

    def scene_index(self, t: float) -> int:
        return max(0, min(len(self.section_bounds) - 2, int(np.searchsorted(self.section_bounds, t, side="right") - 1)))


class FilmRenderer:
    def __init__(
        self,
        config: RenderConfig,
        features_path: str | Path,
        story_path: str | Path,
        media_paths: list[str] | None = None,
    ):
        self.cfg = config
        self.features = FeatureStream(features_path)
        self.story = json.loads(Path(story_path).read_text(encoding="utf-8"))
        self.rng = np.random.default_rng(config.seed)
        self.iw = max(320, int(round(config.width * config.render_scale / 2) * 2))
        self.ih = max(180, int(round(config.height * config.render_scale / 2) * 2))
        self.media = MediaPool(media_paths or [], self.iw, self.ih)
        self.feedback = np.zeros((self.ih, self.iw, 3), np.uint8)
        self.last_frame = np.zeros_like(self.feedback)
        self.yy, self.xx = np.mgrid[0:self.ih, 0:self.iw].astype(np.float32)
        self.nx = (self.xx - self.iw / 2) / max(self.iw, self.ih)
        self.ny = (self.yy - self.ih / 2) / max(self.iw, self.ih)
        self.radius = np.sqrt(self.nx**2 + self.ny**2)
        self.angle = np.arctan2(self.ny, self.nx)
        count = 2600 if self.iw >= 1600 else 1800 if self.iw >= 1000 else 1000
        self.particles = self._init_particles(count)
        self.captions = self.story.get("captions", [])
        self.phrases = [
            "NO SIGNAL", "TRANSMISSION", "BENEATH THE GRID", "MEMORY ERROR",
            "YOU / ME", "SYSTEM FEVER", "STATIC DREAM", "UNDERGROUND",
            "THE CITY IS LISTENING", "ELECTRIC BODY", "DO NOT WAKE",
        ]

    def _init_particles(self, count: int) -> np.ndarray:
        p = np.zeros((count, 4), np.float32)
        p[:, 0] = self.rng.uniform(0, self.iw, count)
        p[:, 1] = self.rng.uniform(0, self.ih, count)
        p[:, 2] = self.rng.uniform(-1, 1, count)
        p[:, 3] = self.rng.uniform(0.2, 1.0, count)
        return p

    def _caption(self, t: float) -> str:
        for c in self.captions:
            if float(c.get("start", 0)) <= t < float(c.get("end", 0)):
                return str(c.get("text", ""))
        return ""

    @staticmethod
    def _ascii(text: str) -> str:
        return text.encode("ascii", "ignore").decode("ascii").strip()

    def _palette(self, frame: np.ndarray, shift: float, brightness: float) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        maps = [cv2.COLORMAP_OCEAN, cv2.COLORMAP_TWILIGHT_SHIFTED, cv2.COLORMAP_BONE, cv2.COLORMAP_MAGMA]
        idx = int(np.clip((shift + 1.0) * 1.999, 0, 3))
        colored = cv2.applyColorMap(gray, maps[idx])
        mix = 0.22 + 0.34 * brightness
        return cv2.addWeighted(frame, 1.0 - mix, colored, mix, 0)

    def _tunnel(self, t: float, e: float, impact: float, bright: float, variant: int = 0) -> np.ndarray:
        phase = (10.0 + variant * 2.0) * self.radius - t * (1.8 + 5.0 * e)
        rings = np.sin(phase * math.tau) * 0.5 + 0.5
        spokes = np.sin(self.angle * (6 + variant * 2 + int(10 * bright)) + t * 0.7) * 0.5 + 0.5
        img = np.clip((rings * 0.72 + spokes * 0.28) * (100 + 155 * impact), 0, 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    def _vector_field(self, t: float, e: float, impact: float, bright: float, variant: int = 0) -> np.ndarray:
        x = self.nx * (7 + variant + 9 * bright)
        y = self.ny * (7 + variant + 9 * bright)
        field = np.sin(x + np.cos(y * 1.7 + t)) + np.cos(y - np.sin(x * 1.3 - t * 1.2))
        field += np.sin((x + y) * (0.7 + variant * .08) + t * (1 + 2 * e)) * impact
        img = np.clip((field + 3) / 6 * 255, 0, 255).astype(np.uint8)
        edges = cv2.Canny(img, 35, 125)
        return cv2.cvtColor(cv2.addWeighted(img, 0.65, edges, 0.9, 0), cv2.COLOR_GRAY2BGR)

    def _particles(self, t: float, e: float, impact: float, bright: float) -> np.ndarray:
        p = self.particles
        cx, cy = self.iw / 2, self.ih / 2
        dx, dy = p[:, 0] - cx, p[:, 1] - cy
        dist = np.sqrt(dx * dx + dy * dy) + 1e-4
        swirl = 0.25 + 2.0 * e
        p[:, 0] += (-dy / dist) * swirl * p[:, 3] + dx / dist * impact * 9
        p[:, 1] += (dx / dist) * swirl * p[:, 3] + dy / dist * impact * 9
        out = (p[:, 0] < 0) | (p[:, 0] >= self.iw) | (p[:, 1] < 0) | (p[:, 1] >= self.ih)
        n = int(out.sum())
        if n:
            a = self.rng.uniform(0, math.tau, n)
            r = self.rng.uniform(2, min(self.iw, self.ih) * 0.16, n)
            p[out, 0], p[out, 1] = cx + np.cos(a) * r, cy + np.sin(a) * r
        frame = np.zeros((self.ih, self.iw, 3), np.uint8)
        coords = p[:, :2].astype(np.int32)
        valid = (coords[:, 0] >= 0) & (coords[:, 0] < self.iw) & (coords[:, 1] >= 0) & (coords[:, 1] < self.ih)
        intensity = np.clip(80 + 175 * (p[:, 3] * (0.35 + e)), 0, 255).astype(np.uint8)
        frame[coords[valid, 1], coords[valid, 0]] = np.stack([intensity[valid]] * 3, axis=1)
        return cv2.GaussianBlur(frame, (0, 0), 0.7 + 2.4 * impact)

    def _halftone(self, base: np.ndarray, e: float, bright: float) -> np.ndarray:
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        cell = max(3, int(14 - 9 * bright))
        small = cv2.resize(gray, (max(1, self.iw // cell), max(1, self.ih // cell)), interpolation=cv2.INTER_AREA)
        small = cv2.threshold(small, int(86 + 75 * (1 - e)), 255, cv2.THRESH_BINARY)[1]
        return cv2.cvtColor(cv2.resize(small, (self.iw, self.ih), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)

    def _pixel_corrupt(self, base: np.ndarray, impact: float, density: float, block: bool = False) -> np.ndarray:
        out = base.copy()
        bands = 2 + int(impact * 18 + density * 9)
        for _ in range(bands):
            y = int(self.rng.integers(0, self.ih))
            h = int(self.rng.integers(2, max(3, self.ih // (12 if block else 28))))
            shift = int(self.rng.integers(-max(2, self.iw // 7), max(3, self.iw // 7)))
            out[y:y + h] = np.roll(out[y:y + h], shift, axis=1)
        if block:
            for _ in range(3 + int(density * 8)):
                x = int(self.rng.integers(0, self.iw)); y = int(self.rng.integers(0, self.ih))
                w = int(self.rng.integers(max(4, self.iw // 30), max(5, self.iw // 5)))
                h = int(self.rng.integers(max(4, self.ih // 40), max(5, self.ih // 8)))
                srcx = int(np.clip(x + self.rng.integers(-self.iw // 5, self.iw // 5), 0, max(0, self.iw - w)))
                ww = min(w, self.iw - x, self.iw - srcx)
                hh = min(h, self.ih - y)
                if ww > 0 and hh > 0:
                    out[y:y+hh, x:x+ww] = base[y:y+hh, srcx:srcx+ww]
        if impact > 0.45:
            b, g, r = cv2.split(out)
            s = max(1, int((impact - .4) * self.iw * .018))
            out = cv2.merge([np.roll(b, s, 1), g, np.roll(r, -s, 1)])
        return out

    def _feedback_mix(self, frame: np.ndarray, e: float, impact: float, strength: float = 0.45) -> np.ndarray:
        center = (self.iw / 2, self.ih / 2)
        scale = 1.002 + 0.010 * e + 0.018 * impact
        angle = (impact - 0.35) * 0.9
        m = cv2.getRotationMatrix2D(center, angle, scale)
        fb = cv2.warpAffine(self.feedback, m, (self.iw, self.ih), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out = cv2.addWeighted(frame, 0.76, fb, strength, -4)
        self.feedback = out.copy()
        return out

    def _powerline_dream(self, t: float, e: float, impact: float, bright: float, shot: int) -> np.ndarray:
        frame = np.zeros((self.ih, self.iw, 3), np.uint8)
        # Pink/blue sky gradient, intentionally reminiscent of infrastructural dream imagery.
        top = np.array([115 + 35 * bright, 35 + 25 * e, 90 + 100 * bright])
        bottom = np.array([25 + 40 * e, 15, 25 + 35 * impact])
        alpha = np.linspace(0, 1, self.ih, dtype=np.float32)[:, None, None]
        frame[:] = np.clip(top * (1 - alpha) + bottom * alpha, 0, 255).astype(np.uint8)
        horizon = int(self.ih * (0.70 + 0.04 * math.sin(t * .3)))
        cv2.rectangle(frame, (0, horizon), (self.iw, self.ih), (8, 7, 10), -1)
        count = 2 + shot % 3
        for i in range(count):
            perspective = 1.0 - i * .25
            x = int(self.iw * (.48 + (i - count/2) * .24 + .06 * math.sin(t*.12+i)))
            base_y = int(horizon + self.ih * .22 * (1-perspective))
            h = int(self.ih * (.48 * perspective + .16))
            w = int(h * .28)
            top_y = base_y - h
            color = (225, 225, 235)
            thick = max(1, int(self.ih / 600))
            cv2.line(frame, (x-w//2, base_y), (x, top_y), color, thick)
            cv2.line(frame, (x+w//2, base_y), (x, top_y), color, thick)
            for frac in [.22, .40, .58, .76]:
                yy = int(top_y + h*frac); ww = int(w*(.28+.72*frac))
                cv2.line(frame, (x-ww, yy), (x+ww, yy), color, thick)
                cv2.line(frame, (x-ww, yy), (x, int(yy-h*.12)), color, thick)
                cv2.line(frame, (x+ww, yy), (x, int(yy-h*.12)), color, thick)
            # Power cables as sagging polylines.
            for side in (-1, 1):
                start = np.array([x + side*w, int(top_y+h*.42)], np.float32)
                end = np.array([self.iw*(1.15 if side>0 else -.15), int(top_y+h*.48+self.ih*.12)], np.float32)
                pts=[]
                for k in range(24):
                    u=k/23
                    p=start*(1-u)+end*u
                    p[1]+=math.sin(math.pi*u)*self.ih*(.06+.03*e)
                    pts.append(p.astype(np.int32))
                cv2.polylines(frame,[np.array(pts)],False,color,thick,cv2.LINE_AA)
        if impact > .55:
            frame = cv2.addWeighted(frame, 1.0, np.full_like(frame, (30, 15, 55)), impact*.16, 0)
        return frame

    def _wireframe_cathedral(self, t: float, e: float, impact: float, bright: float, shot: int) -> np.ndarray:
        frame = np.zeros((self.ih, self.iw, 3), np.uint8)
        van = np.array([self.iw*(.5+.12*math.sin(t*.2)), self.ih*(.38+.08*math.cos(t*.17))])
        color=(160+int(80*bright), 160+int(70*e), 180+int(70*impact))
        for x in np.linspace(-self.iw*.4,self.iw*1.4,18):
            cv2.line(frame,(int(x),self.ih),(int(van[0]),int(van[1])),color,1,cv2.LINE_AA)
        for k in range(1,16):
            u=k/16
            y=int(van[1]+(self.ih-van[1])*(u**1.7))
            cv2.line(frame,(0,y),(self.iw,y),color,1,cv2.LINE_AA)
        center=(int(van[0]),int(van[1]+self.ih*.12))
        sides=4+(shot%5)
        radius=int(min(self.iw,self.ih)*(.15+.06*impact))
        pts=[]
        for i in range(sides):
            a=t*(.3+e*.6)+i*math.tau/sides
            pts.append((int(center[0]+math.cos(a)*radius),int(center[1]+math.sin(a)*radius)))
        cv2.polylines(frame,[np.array(pts)],True,(240,240,250),max(1,int(1+impact*3)),cv2.LINE_AA)
        for p in pts: cv2.line(frame,center,p,(120,150,210),1,cv2.LINE_AA)
        return frame

    def _media_collage(self, t: float, e: float, impact: float, bright: float, scene_idx: int, shot: int) -> np.ndarray:
        frame = np.zeros((self.ih, self.iw, 3), np.uint8)
        frame[:] = (8, 5, 10)
        panels = 3 + shot % 4
        shared = self.media.get(scene_idx + shot, t, speed=.65+e, offset=shot*1.7, zoom=1.05)
        if shared is None:
            shared = self._vector_field(t,e,impact,bright,shot%3)
        for i in range(panels):
            src = np.roll(shared, int(math.sin(i*1.7+shot)*self.iw*.06), axis=1)
            if i % 2:
                src = cv2.flip(src, 1)
            scale = .34 + .12 * ((i+shot)%3)
            pw, ph = int(self.iw*scale), int(self.ih*scale*.75)
            crop=cv2.resize(src,(pw,ph),interpolation=cv2.INTER_AREA)
            angle=(i-panels/2)*(-7+14*math.sin(t*.15+i))
            m=cv2.getRotationMatrix2D((pw/2,ph/2),angle,1.0)
            crop=cv2.warpAffine(crop,m,(pw,ph),borderMode=cv2.BORDER_CONSTANT)
            x=int((self.iw-pw)*(i/max(1,panels-1)) + math.sin(t*.4+i)*self.iw*.04)
            x=min(max(0,x),max(0,self.iw-pw))
            y=int(self.ih*(.12+.58*((i*0.37+shot*.13)%1.0)))
            y=min(max(0,y-ph//2),max(0,self.ih-ph))
            roi=frame[y:y+ph,x:x+pw]
            mask=(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)>3)[...,None]
            roi[:] = np.where(mask,crop,roi)
            cv2.rectangle(frame,(x,y),(x+pw-1,y+ph-1),(235,235,245),max(1,int(self.ih/700)))
        return frame

    def _kinetic_typography(self, t: float, e: float, impact: float, bright: float, scene_idx: int, shot: int) -> np.ndarray:
        frame=np.zeros((self.ih,self.iw,3),np.uint8)
        palettes=[(235,85,180),(240,240,245),(20,20,25),(230,40,60),(255,120,20),(255,70,200)]
        frame[:]=palettes[(scene_idx+shot)%len(palettes)]
        text=self._ascii(self._caption(t)) or self.phrases[(scene_idx+shot)%len(self.phrases)]
        words=text.upper().split() or ["SIGNAL"]
        text=" ".join(words[:4])
        font=cv2.FONT_HERSHEY_SIMPLEX
        scale=max(.8,min(self.iw,self.ih)/420)*(1.25+.65*impact)
        thickness=max(2,int(scale*2.2))
        (tw,th),_=cv2.getTextSize(text,font,scale,thickness)
        x=int(self.iw*.5-tw*.5+math.sin(t*2.1)*self.iw*.09)
        y=int(self.ih*.52+th*.5+math.cos(t*1.7)*self.ih*.08)
        color=(245,245,245) if np.mean(frame[0,0])<150 else (15,15,20)
        cv2.putText(frame,text,(x,y),font,scale,color,thickness,cv2.LINE_AA)
        for i in range(5):
            yy=int((i+1)*self.ih/7 + math.sin(t+i)*20)
            cv2.line(frame,(0,yy),(self.iw,yy),color,1,cv2.LINE_AA)
        return frame

    def _crt_archive(self, t: float, e: float, impact: float, bright: float, scene_idx: int, shot: int) -> np.ndarray:
        frame=np.zeros((self.ih,self.iw,3),np.uint8)
        frame[:]=(7,6,9)
        src=self.media.get(scene_idx+shot,t,speed=.85+e*.4,offset=shot*2.2,zoom=1.03)
        if src is None: src=self._powerline_dream(t,e,impact,bright,shot)
        margin_x=int(self.iw*(.10+.04*math.sin(t*.23)))
        margin_y=int(self.ih*.12)
        screen=cv2.resize(src,(self.iw-2*margin_x,self.ih-2*margin_y))
        screen=self._pixel_corrupt(screen,impact*.7,.35)
        screen[::3]=(screen[::3].astype(np.float32)*.62).astype(np.uint8)
        frame[margin_y:self.ih-margin_y,margin_x:self.iw-margin_x]=screen
        cv2.rectangle(frame,(margin_x,margin_y),(self.iw-margin_x,self.ih-margin_y),(190,190,200),max(2,int(self.ih/240)))
        cv2.circle(frame,(self.iw-margin_x//2,self.ih//2),max(3,int(self.ih*.015)),(40,40,50),-1)
        return frame

    def _rave_documentary(self, t: float, e: float, impact: float, bright: float, scene_idx: int, shot: int) -> np.ndarray:
        src=self.media.get(scene_idx+shot,t,speed=.85+e*.8,offset=shot*1.7,zoom=1.08+impact*.04,
                           pan_x=math.sin(t*.8+shot),pan_y=math.cos(t*.7+shot))
        if src is None:
            src=self._particles(t,e,impact,bright)
            src=cv2.addWeighted(src,1.0,self._powerline_dream(t,e,impact,bright,shot),.35,0)
        # Handheld roll and smear.
        m=cv2.getRotationMatrix2D((self.iw/2,self.ih/2),math.sin(t*7.0+shot)*1.4*(.2+impact),1.03)
        out=cv2.warpAffine(src,m,(self.iw,self.ih),borderMode=cv2.BORDER_REFLECT)
        if impact>.35:
            out=cv2.addWeighted(out,.78,np.roll(out,int(impact*10),axis=1),.32,0)
        return out

    def _signal_city(self, t: float, e: float, impact: float, bright: float, shot: int) -> np.ndarray:
        frame=np.zeros((self.ih,self.iw,3),np.uint8)
        horizon=int(self.ih*.63)
        for i in range(28):
            x=int(i*self.iw/28)
            w=max(2,int(self.iw/34))
            h=int(self.ih*(.05+.38*((math.sin(i*1.37+shot)+1)/2))*(.5+e))
            color=(30+int(100*bright),20+int(70*e),40+int(140*impact))
            cv2.rectangle(frame,(x,horizon-h),(x+w,horizon),color,-1)
        van=(self.iw//2,int(self.ih*.57))
        for x in range(-self.iw,self.iw*2,max(20,self.iw//18)):
            cv2.line(frame,(x,self.ih),van,(90,80,160),1)
        for k in range(12):
            y=int(van[1]+(self.ih-van[1])*(k/12)**1.8)
            cv2.line(frame,(0,y),(self.iw,y),(70,60,120),1)
        scan=int((t*(160+300*e))%self.ih)
        cv2.line(frame,(0,scan),(self.iw,scan),(230,230,250),max(1,int(impact*4)))
        return frame

    def _monolith_scan(self, t: float, e: float, impact: float, bright: float, shot: int) -> np.ndarray:
        frame=np.zeros((self.ih,self.iw,3),np.uint8)
        grad=np.clip((1-self.radius*2.4)*(35+80*e),0,255).astype(np.uint8)
        frame=cv2.cvtColor(grad,cv2.COLOR_GRAY2BGR)
        cx=int(self.iw*(.5+.08*math.sin(t*.25+shot)))
        w=int(self.iw*(.08+.05*bright)); h=int(self.ih*(.48+.16*e))
        y=self.ih//2-h//2
        cv2.rectangle(frame,(cx-w//2,y),(cx+w//2,y+h),(210,210,225),-1)
        cv2.rectangle(frame,(cx-w//2+max(1,w//10),y),(cx+w//2,y+h),(80,90,125),-1)
        beam=int(y+(t*(100+250*e))%max(1,h))
        cv2.line(frame,(cx-w,beam),(cx+w,beam),(255,255,255),max(1,int(2+impact*5)))
        return frame

    def _waveform_sculpture(self, t: float, e: float, impact: float, bright: float, shot: int) -> np.ndarray:
        frame=np.zeros((self.ih,self.iw,3),np.uint8)
        cx,cy=self.iw//2,self.ih//2
        bass=self.features.value("bass",t); mid=self.features.value("mid",t); air=self.features.value("air",t)
        n=180
        pts=[]
        for i in range(n):
            a=i*math.tau/n
            wave=math.sin(a*(3+shot%8)+t*(2+e*5))*mid+math.sin(a*13-t*4)*air*.35
            r=min(self.iw,self.ih)*(.18+.20*bass+.07*wave)
            pts.append((int(cx+math.cos(a)*r),int(cy+math.sin(a)*r)))
        cv2.polylines(frame,[np.array(pts)],True,(220,230,250),max(1,int(1+impact*4)),cv2.LINE_AA)
        for k in range(4):
            rr=int(min(self.iw,self.ih)*(.08+k*.09+impact*.04))
            cv2.circle(frame,(cx,cy),rr,(40+30*k,50+20*k,90+25*k),1,cv2.LINE_AA)
        return frame

    def _render_archetype(self, name: str, t: float, e: float, impact: float, bright: float, scene_idx: int, shot: int, media: np.ndarray | None, density: float) -> np.ndarray:
        if name == "industrial_tunnel": return self._tunnel(t,e,impact,bright,shot%3)
        if name == "vector_field": return self._vector_field(t,e,impact,bright,shot%3)
        if name == "particle_ritual": return self._particles(t,e,impact,bright)
        if name == "halftone_signal": return self._halftone(media if media is not None else self._vector_field(t,e,impact,bright),e,bright)
        if name == "pixel_corruption": return self._pixel_corrupt(media if media is not None else self._tunnel(t,e,impact,bright),impact,density)
        if name == "machine_vision":
            src=media if media is not None else self._particles(t,e,impact,bright)
            gray=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY); edge=cv2.Canny(gray,int(18+75*(1-e)),int(80+110*bright))
            return cv2.cvtColor(edge,cv2.COLOR_GRAY2BGR)
        if name == "liquid_feedback": return self._feedback_mix(media if media is not None else self._vector_field(t,e,impact,bright),e,impact,.58)
        if name == "powerline_dream": return self._powerline_dream(t,e,impact,bright,shot)
        if name == "wireframe_cathedral": return self._wireframe_cathedral(t,e,impact,bright,shot)
        if name == "media_collage": return self._media_collage(t,e,impact,bright,scene_idx,shot)
        if name == "kinetic_typography": return self._kinetic_typography(t,e,impact,bright,scene_idx,shot)
        if name == "crt_archive": return self._crt_archive(t,e,impact,bright,scene_idx,shot)
        if name == "datamosh_blocks": return self._pixel_corrupt(media if media is not None else self.last_frame,impact,density,True)
        if name == "rave_documentary": return self._rave_documentary(t,e,impact,bright,scene_idx,shot)
        if name == "signal_city": return self._signal_city(t,e,impact,bright,shot)
        if name == "monolith_scan": return self._monolith_scan(t,e,impact,bright,shot)
        if name == "waveform_sculpture": return self._waveform_sculpture(t,e,impact,bright,shot)
        return self._vector_field(t,e,impact,bright)

    def _camera(self, frame: np.ndarray, mode: str, t: float, local_t: float, e: float, impact: float, shot: int) -> np.ndarray:
        cx,cy=self.iw/2,self.ih/2
        angle=0.0; scale=1.0; tx=ty=0.0
        if mode == "push": scale=1.0+.035*local_t*(.25+e)
        elif mode == "orbit": angle=math.sin(t*.35+shot)*2.5; scale=1.03+.02*e
        elif mode == "handheld": angle=math.sin(t*7.1+shot)*1.0*(.2+impact); tx=math.sin(t*11.2)*self.iw*.006; ty=math.cos(t*9.7)*self.ih*.008
        elif mode == "reverse": scale=1.16-.03*local_t*(.2+e)
        elif mode == "roll": angle=math.sin(t*.22+shot)*7.0
        elif mode == "crash_zoom": scale=1.0+.16*impact
        m=cv2.getRotationMatrix2D((cx,cy),angle,max(.92,scale)); m[:,2]+=(tx,ty)
        return cv2.warpAffine(frame,m,(self.iw,self.ih),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)

    def _scanlines(self, frame: np.ndarray, strength: float) -> np.ndarray:
        out=frame.copy(); step=3 if self.ih<1200 else 4
        out[::step]=(out[::step].astype(np.float32)*(0.62+0.22*(1-strength))).astype(np.uint8)
        return out

    def _graphic_overlay(self, frame: np.ndarray, symbol: str, t: float, scene_idx: int, impact: float) -> np.ndarray:
        out=frame.copy(); c=(235,235,245); thick=max(1,int(self.ih/800))
        if symbol == "crosshair":
            x=int(self.iw*(.5+.25*math.sin(t*.23+scene_idx))); y=int(self.ih*(.5+.22*math.cos(t*.19)))
            cv2.circle(out,(x,y),int(self.ih*.055),c,thick); cv2.line(out,(x-int(self.iw*.08),y),(x+int(self.iw*.08),y),c,thick); cv2.line(out,(x,y-int(self.ih*.08)),(x,y+int(self.ih*.08)),c,thick)
        elif symbol == "barcode":
            x0=int(self.iw*.04); y0=int(self.ih*.08)
            for i in range(28):
                w=1+(i*7+scene_idx)%5; x=x0+i*max(2,int(self.iw*.0038)); cv2.rectangle(out,(x,y0),(x+w,y0+int(self.ih*.06)),c,-1)
        elif symbol == "window":
            x=int(self.iw*.06); y=int(self.ih*.07); w=int(self.iw*.25); h=int(self.ih*.14)
            cv2.rectangle(out,(x,y),(x+w,y+h),c,thick); cv2.line(out,(x,y+int(h*.22)),(x+w,y+int(h*.22)),c,thick)
        elif symbol == "grid":
            for x in np.linspace(0,self.iw,12): cv2.line(out,(int(x),0),(int(x),self.ih),(150,150,165),1)
            for y in np.linspace(0,self.ih,8): cv2.line(out,(0,int(y)),(self.iw,int(y)),(150,150,165),1)
        elif symbol == "timecode":
            text=f"{int(t//60):02d}:{int(t%60):02d}:{int((t%1)*30):02d}  S{scene_idx:02d}"
            cv2.putText(out,text,(int(self.iw*.04),int(self.ih*.94)),cv2.FONT_HERSHEY_PLAIN,max(1.0,self.ih/550),c,max(1,thick),cv2.LINE_AA)
        elif symbol == "cursor":
            x=int(self.iw*(.5+.3*math.sin(t*.4))); y=int(self.ih*(.5+.25*math.cos(t*.33)))
            pts=np.array([(x,y),(x+int(self.iw*.018),y+int(self.ih*.05)),(x+int(self.iw*.007),y+int(self.ih*.04))])
            cv2.fillPoly(out,[pts],c)
        if impact>.82:
            cv2.rectangle(out,(int(self.iw*.02),int(self.ih*.02)),(int(self.iw*.98),int(self.ih*.98)),c,thick)
        return out

    def _typography(self, frame: np.ndarray, mode: str, t: float, scene_idx: int, shot: int) -> np.ndarray:
        if not self.cfg.typography or mode == "none": return frame
        text=self._ascii(self._caption(t))
        if not text and mode in {"huge","fragment","terminal"}:
            text=self.phrases[(scene_idx+shot)%len(self.phrases)]
        if not text: return frame
        out=frame.copy(); text=text.upper()[:92]
        if mode == "subtitle":
            scale=max(.55,self.ih/920); thick=max(1,int(scale*2)); margin=int(self.iw*.08)
            (tw,th),_=cv2.getTextSize(text,cv2.FONT_HERSHEY_SIMPLEX,scale,thick)
            if tw>self.iw-margin*2:
                text=text[:max(12,int(len(text)*(self.iw-margin*2)/max(1,tw)))]
                (tw,th),_=cv2.getTextSize(text,cv2.FONT_HERSHEY_SIMPLEX,scale,thick)
            x=(self.iw-tw)//2; y=int(self.ih*.90)
            cv2.rectangle(out,(x-int(self.iw*.02),y-th-int(self.ih*.018)),(x+tw+int(self.iw*.02),y+int(self.ih*.014)),(25,20,160),-1)
            cv2.putText(out,text,(x,y),cv2.FONT_HERSHEY_SIMPLEX,scale,(245,245,250),thick,cv2.LINE_AA)
        elif mode == "huge":
            scale=max(1.0,min(self.iw,self.ih)/330); thick=max(2,int(scale*2.5)); word=text.split()[0][:15]
            (tw,th),_=cv2.getTextSize(word,cv2.FONT_HERSHEY_SIMPLEX,scale,thick)
            cv2.putText(out,word,(int(self.iw*.5-tw*.5),int(self.ih*.55+th*.5)),cv2.FONT_HERSHEY_SIMPLEX,scale,(245,245,250),thick,cv2.LINE_AA)
        elif mode == "fragment":
            words=text.split()[:5]
            for i,w in enumerate(words):
                scale=max(.55,self.ih/800)*(1+.25*((i+shot)%3)); x=int((.04+.18*i)*self.iw)%max(1,self.iw-40); y=int(self.ih*(.18+.16*(i%4)))
                cv2.putText(out,w,(x,y),cv2.FONT_HERSHEY_SIMPLEX,scale,(245,245,250),max(1,int(scale*2)),cv2.LINE_AA)
        else:
            scale=max(.5,self.ih/1050); y=int(self.ih*.12)
            cv2.putText(out,"> "+text,(int(self.iw*.05),y),cv2.FONT_HERSHEY_PLAIN,scale,(180,255,210),max(1,int(scale)),cv2.LINE_AA)
        return out

    def _transition(self, frame: np.ndarray, scene: dict, local_t: float, impact: float) -> np.ndarray:
        dur=.20+.22*self.cfg.edit_density
        if local_t>=dur: return frame
        p=np.clip(local_t/dur,0,1); kind=scene.get("transition","cut")
        if kind == "flash": return cv2.addWeighted(frame,p,np.full_like(frame,255),1-p,0)
        if kind == "wipe":
            out=self.last_frame.copy(); x=int(self.iw*p); out[:,:x]=frame[:,:x]; return out
        if kind == "pixel":
            pix=max(1,int((1-p)*42+1)); small=cv2.resize(frame,(max(1,self.iw//pix),max(1,self.ih//pix))); return cv2.resize(small,(self.iw,self.ih),interpolation=cv2.INTER_NEAREST)
        if kind == "luma":
            mask=(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY) < p*255)[...,None]; return np.where(mask,frame,self.last_frame).astype(np.uint8)
        if kind == "feedback": return cv2.addWeighted(frame,p,self.last_frame,1-p,0)
        return frame

    def frame(self, t: float) -> np.ndarray:
        e=self.features.value("energy",t)
        impact=max(self.features.value("impact",t),self.features.beat_pulse(t))
        bright=self.features.value("brightness",t)
        texture=self.features.value("texture",t)
        flux=self.features.value("flux",t)
        scene_idx=self.features.scene_index(t)
        scene=self.story["scenes"][scene_idx % len(self.story["scenes"])]
        local_t=max(0.0,t-float(scene["start"]))
        shot_seconds=max(.12,float(scene.get("shot_seconds",2.0)))
        shot=int(local_t/shot_seconds)
        density=float(scene["glitch_density"])
        shift=float(scene["palette_shift"])
        archetype=scene["archetype"]
        # Alternating micro-shots are a key 0.2 change: music sections no longer equal one static visual shot.
        if shot % 4 == 3 and self.cfg.edit_density > .35:
            archetype=scene.get("alt_archetype",archetype)
        self_media = {"media_collage", "crt_archive", "rave_documentary"}
        media = None
        if archetype not in self_media:
            media=self.media.get(scene_idx+shot,t,speed=.70+e*.85,offset=shot*1.13,zoom=1.02+impact*.035,
                                 pan_x=math.sin(t*.31+shot),pan_y=math.cos(t*.27+shot))
        base=self._render_archetype(archetype,t,e,impact,bright,scene_idx,shot,media,density)

        if media is not None and archetype not in {"halftone_signal","pixel_corruption","machine_vision","liquid_feedback","media_collage","crt_archive","rave_documentary","datamosh_blocks"}:
            mix=float(scene["media_mix"])*(.20+.70*e)
            base=cv2.addWeighted(base,1.0-mix,media,mix,0)

        base=self._camera(base,scene.get("camera_mode","locked"),t,local_t,e,impact,shot)
        if archetype not in {"liquid_feedback","datamosh_blocks"}:
            base=self._feedback_mix(base,e,impact,.26+.22*texture)
        event=(impact>.48 or flux>.65)
        if density>.25 and event and (shot%2==0 or impact>.75):
            base=self._pixel_corrupt(base,impact,density,block=flux>.80)
        base=self._palette(base,shift,bright)
        base=self._graphic_overlay(base,scene.get("graphic_symbol","timecode"),t,scene_idx,impact)
        base=self._typography(base,scene.get("typography_mode","none"),t,scene_idx,shot)
        base=self._scanlines(base,.18+texture*.50)
        filter_name=self.cfg.filter_name if self.cfg.filter_name != "auto" else scene.get("filter","none")
        base=apply_filter(base,filter_name,self.cfg.filter_intensity,self.rng)
        base=self._transition(base,scene,local_t,impact)

        strobe=min(max(self.cfg.strobe,0.0),0.30 if self.cfg.safe_flashes else 0.45)
        if strobe>0 and impact>.91 and math.sin(t*37.0)>0.88:
            base=cv2.addWeighted(base,1.0-strobe,np.full_like(base,255),strobe,0)

        self.last_frame=base.copy()
        if (self.iw,self.ih)!=(self.cfg.width,self.cfg.height):
            base=cv2.resize(base,(self.cfg.width,self.cfg.height),interpolation=cv2.INTER_CUBIC)
        return base

    def close(self) -> None:
        self.media.close()


def _available_encoders() -> str:
    if not shutil.which("ffmpeg"):
        return ""
    try:
        return subprocess.check_output(["ffmpeg","-hide_banner","-encoders"],stderr=subprocess.DEVNULL,text=True,timeout=10)
    except Exception:
        return ""


def resolve_encoder(requested: str, output: Path) -> str:
    if output.suffix.lower()==".avi":
        return "mpeg4"
    if requested != "auto":
        return requested
    enc=_available_encoders()
    # FFmpeg may advertise hardware encoders even when the corresponding
    # runtime/driver is unavailable. Require a matching host signal.
    if shutil.which("nvidia-smi") and "h264_nvenc" in enc:
        return "h264_nvenc"
    if platform.system() == "Windows" and "h264_qsv" in enc:
        return "h264_qsv"
    if platform.system() == "Windows" and "h264_amf" in enc:
        return "h264_amf"
    return "libx264"


def _ffmpeg_encoder_args(cfg: RenderConfig, output: Path) -> list[str]:
    encoder=resolve_encoder(cfg.encoder,output)
    if output.suffix.lower()==".avi":
        return ["-c:v","mpeg4","-q:v","2","-c:a","libmp3lame","-b:a","320k"]
    if encoder in {"h264_nvenc","hevc_nvenc"}:
        return ["-c:v",encoder,"-preset","p5","-tune","hq","-rc","vbr","-cq",str(cfg.crf),"-b:v","0","-c:a","aac","-b:a","320k"]
    if encoder in {"h264_amf","hevc_amf"}:
        return ["-c:v",encoder,"-quality","quality","-qp_i",str(cfg.crf),"-qp_p",str(cfg.crf),"-c:a","aac","-b:a","320k"]
    if encoder in {"h264_qsv","hevc_qsv"}:
        return ["-c:v",encoder,"-preset","medium","-global_quality",str(cfg.crf),"-c:a","aac","-b:a","320k"]
    if encoder in {"libx265","libx264"}:
        return ["-c:v",encoder,"-preset",cfg.preset,"-crf",str(cfg.crf),"-c:a","aac","-b:a","320k"]
    return ["-c:v","libx264","-preset",cfg.preset,"-crf",str(cfg.crf),"-c:a","aac","-b:a","320k"]


def _audio_filter(mode: str) -> list[str]:
    if mode in {"normalize","streaming"}:
        return ["-af","loudnorm=I=-14:TP=-1.0:LRA=11"]
    if mode == "cinema":
        return ["-af","highpass=f=20,lowpass=f=20000,loudnorm=I=-16:TP=-1.5:LRA=12"]
    if mode == "club":
        return ["-af","highpass=f=20,alimiter=limit=0.95,loudnorm=I=-10:TP=-0.8:LRA=8"]
    return []


def render_film(
    audio_path: str | Path,
    output_path: str | Path,
    features_path: str | Path,
    story_path: str | Path,
    config: RenderConfig,
    duration: float,
    media_paths: list[str] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg não foi encontrado no PATH.")
    output=Path(output_path); output.parent.mkdir(parents=True,exist_ok=True)
    total_frames=max(1,int(math.ceil(duration*config.fps)))
    cmd=[
        "ffmpeg","-hide_banner","-loglevel","warning","-y",
        "-f","rawvideo","-vcodec","rawvideo","-pix_fmt","bgr24",
        "-s",f"{config.width}x{config.height}","-r",str(config.fps),"-i","-",
        "-i",str(Path(audio_path)),"-map","0:v:0","-map","1:a:0",
        *_ffmpeg_encoder_args(config,output),*_audio_filter(config.audio_mode),
        "-pix_fmt","yuv420p","-movflags","+faststart","-t",f"{duration:.6f}","-shortest",str(output),
    ]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    renderer=FilmRenderer(config,features_path,story_path,media_paths)
    try:
        assert process.stdin is not None
        for frame_index in range(total_frames):
            t=min(duration,frame_index/config.fps)
            process.stdin.write(renderer.frame(t).tobytes())
            if progress and (frame_index%max(1,int(config.fps))==0 or frame_index==total_frames-1):
                progress(frame_index+1,total_frames)
        process.stdin.close(); code=process.wait()
        if code!=0: raise RuntimeError(f"FFmpeg encerrou com código {code}.")
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg interrompeu o render. Verifique codec, espaço em disco e formato de saída.") from exc
    finally:
        renderer.close()
        if process.poll() is None: process.terminate()
