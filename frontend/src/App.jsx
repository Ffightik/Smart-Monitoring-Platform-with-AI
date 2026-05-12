import { useState, useRef, useEffect, useCallback } from "react";

const API = "/api/v1";

const getToken  = ()     => localStorage.getItem("hp_token");
const getUser   = ()     => { try { return JSON.parse(localStorage.getItem("hp_user")||"null"); } catch { return null; } };
const saveAuth  = (t,u)  => { localStorage.setItem("hp_token",t); localStorage.setItem("hp_user",JSON.stringify(u)); };
const clearAuth = ()     => { localStorage.removeItem("hp_token"); localStorage.removeItem("hp_user"); };
const authHdr   = ()     => ({"Content-Type":"application/json","Authorization":`Bearer ${getToken()}`});
const getProfile= ()     => { try { return JSON.parse(localStorage.getItem("hp_profile")||"{}"); } catch { return {}; } };
const saveProfile= p     => localStorage.setItem("hp_profile", JSON.stringify(p));

const css = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Nunito:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&display=swap');

@keyframes gradientShift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes glowPulse {
  0%,100% { box-shadow: 0 0 20px rgba(139,92,246,.35), 0 4px 20px rgba(99,102,241,.25); }
  50%      { box-shadow: 0 0 40px rgba(139,92,246,.55), 0 4px 32px rgba(99,102,241,.45); }
}
@keyframes shimmer {
  0%   { background-position: -200% center; }
  100% { background-position: 200% center; }
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --cream:  #f0eeff;
  --warm:   #e8e4ff;
  --paper:  #f8f7ff;
  --ink:    #1e1b4b;
  --ink2:   #3730a3;
  --ink3:   #7c7ab5;
  --blue:   #6366f1;
  --blue-l: #e0e7ff;
  --blue-g: rgba(99,102,241,0.08);
  --red:    #f472b6;
  --red-l:  #fce7f3;
  --green:  #34d399;
  --green-l:#d1fae5;
  --amber:  #a78bfa;
  --amber-l:#ede9fe;
  --violet: #8b5cf6;
  --violet-l:#f5f3ff;
  --pink:   #ec4899;
  --pink-l: #fdf2f8;
  --glass:  rgba(255,255,255,0.60);
  --glass-hi:rgba(255,255,255,0.82);
  --shadow: 0 2px 24px rgba(99,102,241,0.10);
  --shadow-lg: 0 8px 48px rgba(99,102,241,0.18);
  --border: rgba(139,92,246,0.12);
  --border-hi: rgba(139,92,246,0.22);
  --r: 20px; --r-lg: 28px; --r-xl: 36px;
  --font: 'Nunito', sans-serif;
  --serif: 'Playfair Display', serif;
  --grad: linear-gradient(135deg, #c7d2fe, #e9d5ff, #fce7f3, #c7d2fe);
  --grad-btn: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899, #6366f1);
}

html, body, #root {
  height: 100%; background: var(--cream);
  color: var(--ink); font-family: var(--font);
  -webkit-font-smoothing: antialiased;
}
body { background: linear-gradient(135deg,#f0eeff 0%,#fce7f3 40%,#e0e7ff 70%,#f5f3ff 100%);
  background-size: 400% 400%;
  animation: gradientShift 12s ease infinite; }

/* ── Noise texture overlay ── */
body::before {
  content: ''; position: fixed; inset: 0; z-index: 0;
  pointer-events: none; opacity: .015;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}

/* ══ AUTH ══ */
.auth-page {
  min-height: 100vh; display: flex; position: relative; overflow: hidden;
}
.auth-left {
  width: 420px; flex-shrink: 0;
  background: linear-gradient(160deg, #312e81 0%, #4c1d95 40%, #831843 100%);
  background-size: 200% 200%; animation: gradientShift 8s ease infinite;
  padding: 48px 48px 48px;
  display: flex; flex-direction: column;
  position: relative; overflow: hidden;
}
.auth-left::before {
  content: ''; position: absolute; top: -100px; right: -100px;
  width: 300px; height: 300px; border-radius: 50%;
  background: radial-gradient(circle, rgba(196,181,253,.4), transparent 70%);
}
.auth-left::after {
  content: ''; position: absolute; bottom: -80px; left: -80px;
  width: 240px; height: 240px; border-radius: 50%;
  background: radial-gradient(circle, rgba(244,114,182,.3), transparent 70%);
}
.auth-logo-dark {
  display: flex; align-items: center; gap: 10px; margin-bottom: 48px;
  position: relative; z-index: 1;
}
.auth-logo-dot {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #c7d2fe, #e9d5ff);
  display: flex; align-items: center; justify-content: center; font-size: 14px;
}
.auth-logo-name { font-size: 17px; font-weight: 600; color: white; letter-spacing: -.3px; }
.auth-tagline {
  font-family: var(--serif); font-size: 36px; line-height: 1.2;
  color: white; margin-bottom: 24px; position: relative; z-index: 1;
}
.auth-tagline em { color: #93c5fd; font-style: italic; }
.auth-desc { font-size: 14px; color: rgba(255,255,255,.55); line-height: 1.7; position: relative; z-index: 1; }
.auth-stats {
  margin-top: auto; display: grid; grid-template-columns: 1fr 1fr;
  gap: 12px; position: relative; z-index: 1;
}
.auth-stat {
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1);
  border-radius: 16px; padding: 16px;
}
.auth-stat-val { font-size: 22px; font-weight: 700; color: white; }
.auth-stat-lbl { font-size: 11px; color: rgba(255,255,255,.45); margin-top: 2px; }

.auth-right {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 48px; background: transparent;
}
.auth-card {
  width: 100%; max-width: 400px;
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(60px) saturate(200%);
  border: 1.5px solid rgba(139,92,246,.2);
  border-radius: var(--r-xl); padding: 40px;
  box-shadow: 0 8px 48px rgba(139,92,246,.15), 0 0 0 1px rgba(255,255,255,.5) inset;
}
.auth-card-title { font-size: 24px; font-weight: 600; letter-spacing: -.4px; margin-bottom: 4px; }
.auth-card-sub   { font-size: 14px; color: var(--ink3); margin-bottom: 28px; }
.field { margin-bottom: 14px; }
.field label { display: block; font-size: 11px; font-weight: 600; color: var(--ink3); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .07em; }
.field input {
  width: 100%; background: rgba(255,255,255,.8);
  border: 1.5px solid var(--border); border-radius: 14px;
  padding: 12px 16px; color: var(--ink); font-family: var(--font); font-size: 15px; outline: none;
  transition: border-color .2s, box-shadow .2s;
}
.field input:focus { border-color: var(--violet); box-shadow: 0 0 0 3px rgba(139,92,246,.15); }
.field input::placeholder { color: var(--ink3); }
.auth-btn {
  width: 100%; padding: 14px; border-radius: 980px; border: none;
  background: var(--grad-btn); background-size: 300% 100%;
  animation: shimmer 3s linear infinite;
  color: white; font-family: var(--font); font-size: 15px; font-weight: 600;
  cursor: pointer; transition: all .2s; margin-top: 6px; letter-spacing: -.1px;
  box-shadow: 0 4px 24px rgba(139,92,246,.35);
}
.auth-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 36px rgba(139,92,246,.55); animation-play-state: paused; }
.auth-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; }
.auth-err { font-size: 13px; color: var(--red); margin-top: 10px; padding: 10px 14px; background: var(--red-l); border-radius: 10px; text-align: center; }
.auth-switch { text-align: center; margin-top: 20px; font-size: 14px; color: var(--ink3); }
.auth-link { color: var(--blue); cursor: pointer; background: none; border: none; font-family: var(--font); font-size: 14px; font-weight: 600; }

/* ══ SHELL ══ */
.shell { display: flex; height: 100vh; overflow: hidden; position: relative; }

/* ══ SIDEBAR ══ */
.sidebar {
  width: 240px; flex-shrink: 0;
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(40px) saturate(200%);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column; padding: 28px 0 20px;
  position: relative; z-index: 10;
}
.logo { padding: 0 20px 32px; display: flex; align-items: center; gap: 10px; }
.logo-dot {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg,var(--blue),var(--violet)); display: flex; align-items: center; justify-content: center; font-size: 13px;
}
.logo-text { font-size: 16px; font-weight: 600; letter-spacing: -.3px; }
.nav-lbl { font-size: 10px; font-weight: 600; color: var(--ink3); letter-spacing: .1em; text-transform: uppercase; padding: 0 20px 10px; }
.nav-btn {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 12px; margin: 0 8px 2px;
  font-size: 14px; font-weight: 500; color: var(--ink2);
  cursor: pointer; border: none; background: none;
  width: calc(100% - 16px); text-align: left; transition: all .18s;
}
.nav-btn:hover { color: var(--ink); background: rgba(26,24,20,.06); }
.nav-btn.active { color: var(--violet); background: rgba(139,92,246,.1); font-weight: 600; border: 1px solid rgba(139,92,246,.15); }
.nav-btn.active .nav-icon { background: linear-gradient(135deg,var(--blue),var(--violet)); color: white; }
.nav-icon {
  width: 28px; height: 28px; border-radius: 8px; font-size: 13px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(26,24,20,.06); transition: all .18s; flex-shrink: 0;
}
.sidebar-foot { margin-top: auto; padding: 14px 20px; border-top: 1px solid var(--border); }
.user-row { display: flex; align-items: center; gap: 10px; cursor: pointer; border-radius: 12px; padding: 6px 8px; margin: -6px -8px; transition: background .18s; }
.user-row:hover { background: rgba(26,24,20,.06); }
.user-av {
  width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg,var(--blue),var(--violet));
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: white; flex-shrink: 0;
}
.user-name  { font-size: 13px; font-weight: 600; }
.user-email { font-size: 11px; color: var(--ink3); }
.live-badge { margin-left: auto; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 20px; }
.live-on  { background: var(--green-l);  color: var(--green); }
.live-off { background: var(--red-l);    color: var(--red); }
.logout-btn { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 10px; margin: 8px 8px 0; font-size: 13px; color: var(--ink3); cursor: pointer; border: none; background: none; width: calc(100% - 16px); transition: all .18s; }
.logout-btn:hover { color: var(--pink); background: var(--pink-l); }

/* ══ MAIN ══ */
.main { flex: 1; overflow-y: auto; background: transparent; }
.page { padding: 40px 44px 100px; min-height: 100%; animation: fadeUp .35s ease; }
@keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:none} }
.page-hdr { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
.page-title { font-family: var(--serif); font-size: 38px; letter-spacing: -.5px; line-height: 1; }
.page-sub   { font-size: 14px; color: var(--ink3); margin-top: 4px; }

/* ══ BENTO GRID ══ */
.bento { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }

/* Glass card base */
.gc {
  background: var(--glass-hi);
  backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 24px; position: relative; overflow: hidden;
  box-shadow: var(--shadow);
  transition: box-shadow .25s, transform .2s;
}
.gc:hover { box-shadow: var(--shadow-lg); transform: translateY(-1px); }

/* Bento sizes */
.b-8  { grid-column: span 8; }
.b-7  { grid-column: span 7; }
.b-6  { grid-column: span 6; }
.b-5  { grid-column: span 5; }
.b-4  { grid-column: span 4; }
.b-3  { grid-column: span 3; }
.b-full { grid-column: 1 / -1; }

/* Card accent bars */
.gc-accent { position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: var(--r-lg) var(--r-lg) 0 0; }
.ac-blue   { background: linear-gradient(90deg, #6366f1, #a5b4fc); }
.ac-red    { background: linear-gradient(90deg, #ec4899, #f9a8d4); }
.ac-green  { background: linear-gradient(90deg, #34d399, #6ee7b7); }
.ac-amber  { background: linear-gradient(90deg, #a78bfa, #c4b5fd); }
.ac-violet { background: linear-gradient(90deg, #8b5cf6, #c4b5fd); }

/* Card content */
.card-label { font-size: 11px; font-weight: 600; color: var(--ink3); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 8px; }
.card-val   { font-family: var(--serif); font-size: 42px; line-height: 1; letter-spacing: -1px; }
.card-unit  { font-family: var(--font); font-size: 16px; font-weight: 400; color: var(--ink3); margin-left: 4px; }
.card-sub   { font-size: 12px; color: var(--ink3); margin-top: 6px; }
.card-tag   {
  display: inline-flex; align-items: center; padding: 3px 10px;
  border-radius: 20px; font-size: 11px; font-weight: 600;
  margin-top: 10px;
}
.tag-blue   { background: var(--blue-l);   color: var(--blue); }
.tag-red    { background: var(--red-l);    color: var(--red); }
.tag-green  { background: var(--green-l);  color: var(--green); }
.tag-amber  { background: var(--amber-l);  color: var(--amber); }
.tag-violet { background: var(--violet-l); color: var(--violet); }

/* Prediction card */
.pred-hero {
  background: linear-gradient(135deg, #312e81 0%, #4c1d95 50%, #831843 100%);
  background-size: 200% 200%; animation: gradientShift 8s ease infinite;
  border-radius: var(--r-lg); padding: 28px 32px;
  margin-bottom: 14px; position: relative; overflow: hidden;
}
.pred-hero::before {
  content: ''; position: absolute; top: -80px; right: -80px;
  width: 240px; height: 240px; border-radius: 50%;
  background: radial-gradient(circle, rgba(37,99,235,.35), transparent 70%);
}
.pred-hero::after {
  content: ''; position: absolute; bottom: -60px; left: 40%;
  width: 200px; height: 200px; border-radius: 50%;
  background: radial-gradient(circle, rgba(124,58,237,.2), transparent 70%);
}
.pred-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10px; font-weight: 700; color: #93c5fd;
  text-transform: uppercase; letter-spacing: .12em; margin-bottom: 12px;
  background: rgba(37,99,235,.2); border: 1px solid rgba(37,99,235,.3);
  padding: 4px 10px; border-radius: 20px;
}
.pred-title { font-family: var(--serif); font-size: 22px; color: white; margin-bottom: 6px; line-height: 1.2; }
.pred-desc  { font-size: 13px; color: rgba(255,255,255,.5); line-height: 1.65; max-width: 580px; margin-bottom: 20px; }
.pred-models { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; position: relative; z-index: 1; }
.pred-card {
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1);
  border-radius: 16px; padding: 16px;
}
.pred-card-lbl  { font-size: 10px; color: rgba(255,255,255,.4); text-transform: uppercase; letter-spacing: .1em; margin-bottom: 8px; font-weight: 600; }
.pred-pill { display: inline-flex; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 8px; }
.pp-high   { background: rgba(239,68,68,.25);  color: #fca5a5; }
.pp-medium { background: rgba(22,163,74,.25);  color: #86efac; }
.pp-low    { background: rgba(96,165,250,.25); color: #93c5fd; }
.pp-gray   { background: rgba(255,255,255,.1); color: rgba(255,255,255,.5); }
.pred-bar  { height: 2px; background: rgba(255,255,255,.1); border-radius: 2px; }
.pred-fill { height: 100%; border-radius: 2px; transition: width 1s; }
.pred-conf { font-size: 11px; color: rgba(255,255,255,.35); margin-top: 5px; }

/* Bar chart */
.barchart { width: 100%; }
.barchart-svg { width: 100%; display: block; overflow: visible; }
.time-labels { display: flex; justify-content: space-between; margin-top: 5px; }
.time-lbl { font-size: 10px; color: var(--ink3); font-variant-numeric: tabular-nums; }

/* Activity card expandable */
.ac-card {
  background: var(--glass-hi); backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid var(--border); border-radius: var(--r-lg);
  padding: 20px 22px; cursor: pointer; position: relative; overflow: hidden;
  box-shadow: var(--shadow); transition: all .25s;
}
.ac-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-1px); }
.ac-card.expanded {
  position: fixed; left: 260px; right: 32px; top: 50%; transform: translateY(-50%); z-index: 200;
  border-radius: var(--r-xl); cursor: default;
  box-shadow: 0 40px 100px rgba(99,102,241,.15); overflow-y: auto; padding: 28px 32px;
  backdrop-filter: blur(60px) saturate(220%); max-height: calc(100vh - 64px);
}
.ac-overlay { position: fixed; inset: 0; z-index: 199; background: rgba(26,24,20,.35); backdrop-filter: blur(8px); }
.ac-name  { font-size: 12px; font-weight: 600; color: var(--ink3); text-transform: uppercase; letter-spacing: .07em; margin-bottom: 6px; }
.ac-val   { font-family: var(--serif); font-size: 32px; line-height: 1; letter-spacing: -.5px; }
.ac-unit  { font-family: var(--font); font-size: 14px; color: var(--ink3); margin-left: 3px; }
.ac-sub   { font-size: 12px; color: var(--ink3); margin-top: 4px; margin-bottom: 14px; }
.ac-close { position: absolute; top: 16px; right: 16px; width: 28px; height: 28px; border-radius: 50%; background: rgba(26,24,20,.08); border: none; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.ac-stats { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 20px; }
.ac-stat  { background: rgba(26,24,20,.04); border-radius: 14px; padding: 14px 16px; }
.ac-stat-l { font-size: 10px; color: var(--ink3); text-transform: uppercase; letter-spacing: .07em; margin-bottom: 4px; }
.ac-stat-v { font-family: var(--serif); font-size: 22px; }
.hint { position: absolute; bottom: 10px; right: 14px; font-size: 10px; color: var(--ink3); opacity: 0; transition: opacity .2s; letter-spacing: .04em; }
.ac-card:not(.expanded):hover .hint { opacity: 1; }

/* Rings */
.rings-bento {
  background: var(--glass-hi); backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid var(--border); border-radius: var(--r-lg); padding: 24px;
  box-shadow: var(--shadow);
}
.ring-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.ring-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.ring-lbl { font-size: 13px; color: var(--ink2); flex: 0 0 72px; }
.ring-bar { flex: 1; height: 6px; background: rgba(26,24,20,.08); border-radius: 3px; overflow: hidden; }
.ring-fill { height: 100%; border-radius: 3px; transition: width 1.2s; }
.ring-pct { font-size: 12px; font-weight: 700; width: 36px; text-align: right; }

/* Insight cards */
.insight-card {
  background: var(--glass-hi); backdrop-filter: blur(30px);
  border: 1px solid var(--border); border-radius: var(--r-lg); padding: 22px;
  box-shadow: var(--shadow); transition: all .25s;
}
.insight-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-1px); }
.insight-icon { font-size: 24px; margin-bottom: 10px; }
.insight-title { font-size: 15px; font-weight: 600; margin-bottom: 5px; letter-spacing: -.2px; }
.insight-text  { font-size: 13px; color: var(--ink2); line-height: 1.6; }

/* Upload */
.upload-zone {
  background: var(--glass-hi); backdrop-filter: blur(30px) saturate(180%);
  border: 2px dashed var(--border-hi); border-radius: var(--r-xl);
  padding: 52px 40px; text-align: center; cursor: pointer; transition: all .25s;
  display: flex; flex-direction: column; align-items: center; gap: 12px; min-height: 240px; justify-content: center;
}
.upload-zone:hover, .upload-zone.drag {
  border-color: var(--blue); background: var(--blue-g); transform: scale(1.005);
}
.upload-glyph {
  width: 60px; height: 60px; border-radius: 18px;
  background: var(--blue-l); display: flex; align-items: center; justify-content: center; font-size: 24px;
}
.upload-title { font-size: 20px; font-weight: 600; letter-spacing: -.3px; }
.upload-sub { font-size: 14px; color: var(--ink3); line-height: 1.5; }
.upload-sub em { color: var(--blue); font-style: normal; font-weight: 600; }
.progress-track { height: 2px; background: var(--border); border-radius: 2px; margin-top: 16px; overflow: hidden; }
.progress-fill  { height: 100%; background: var(--blue); border-radius: 2px; transition: width .4s; }

/* Buttons */
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 11px 24px; border-radius: 980px; border: none; font-family: var(--font); font-size: 14px; font-weight: 600; cursor: pointer; transition: all .2s; }
.btn-dark {
  background: var(--grad-btn); background-size: 300% 100%;
  animation: shimmer 3s linear infinite;
  color: white; box-shadow: 0 4px 20px rgba(139,92,246,.3);
}
.btn-dark:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(139,92,246,.5); animation-play-state: paused; }
.btn-dark:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; animation: none; }
.btn-ghost { background: rgba(26,24,20,.06); color: var(--ink); border: 1px solid var(--border-hi); }
.btn-ghost:hover { background: rgba(26,24,20,.10); }
.btn-sm { padding: 8px 16px; font-size: 13px; }
.fmt-item { display: flex; align-items: center; gap: 12px; background: rgba(26,24,20,.04); border: 1px solid var(--border); border-radius: 14px; padding: 12px 16px; }
.fmt-icon { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 15px; }
.fmt-name { font-size: 13px; font-weight: 600; }
.fmt-desc { font-size: 11px; color: var(--ink3); margin-top: 1px; }

/* Profile */
.prof-section { background: var(--glass-hi); backdrop-filter: blur(30px); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 24px 26px; box-shadow: var(--shadow); }
.prof-section.full { grid-column: 1 / -1; }
.ps-title { font-size: 12px; font-weight: 700; color: var(--violet); text-transform: uppercase; letter-spacing: .09em; margin-bottom: 16px; display: flex; align-items: center; gap: 7px; }
.pf { margin-bottom: 13px; }
.pf label { display: block; font-size: 11px; font-weight: 700; color: var(--ink2); margin-bottom: 5px; text-transform: uppercase; letter-spacing: .07em; }
.pf input, .pf select, .pf textarea {
  width: 100%; background: rgba(255,255,255,.8); border: 1.5px solid var(--border); border-radius: 12px;
  padding: 10px 14px; color: var(--ink); font-family: var(--font); font-size: 14px; outline: none;
  transition: border-color .2s, box-shadow .2s;
}
.pf input:focus, .pf select:focus, .pf textarea:focus { border-color: var(--violet); box-shadow: 0 0 0 3px rgba(139,92,246,.12); }
.pf select option { background: white; }
.pf textarea { resize: vertical; min-height: 90px; line-height: 1.55; }
.pf-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.save-btn {
  display: inline-flex; align-items: center; gap: 7px; padding: 11px 24px;
  border-radius: 980px; border: none;
  background: var(--grad-btn); background-size: 300% 100%;
  animation: shimmer 3s linear infinite;
  color: white; font-family: var(--font); font-size: 14px; font-weight: 600;
  cursor: pointer; transition: all .2s; box-shadow: 0 4px 20px rgba(139,92,246,.3);
}
.save-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(139,92,246,.5); animation-play-state: paused; }
.save-toast { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; color: var(--green); margin-left: 12px; animation: fadeOut 2.5s ease forwards; }
@keyframes fadeOut { 0%{opacity:0} 10%{opacity:1} 70%{opacity:1} 100%{opacity:0} }
.goal-opt { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border: 1.5px solid var(--border); border-radius: 14px; cursor: pointer; transition: all .2s; margin-bottom: 8px; background: rgba(255,255,255,.7); color: var(--ink); font-weight: 500; }
.goal-opt:hover { border-color: var(--blue); background: var(--blue-g); }
.goal-opt.sel { border-color: var(--blue); background: var(--blue-g); }
.goal-radio { width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--border-hi); margin-left: auto; flex-shrink: 0; transition: all .2s; display: flex; align-items: center; justify-content: center; }
.goal-opt.sel .goal-radio { border-color: var(--blue); background: var(--blue); }
.goal-opt.sel .goal-radio::after { content: ''; width: 6px; height: 6px; border-radius: 50%; background: white; }
.allergy-tags { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 10px; }
.a-tag { display: inline-flex; align-items: center; gap: 5px; padding: 4px 11px; border-radius: 20px; font-size: 12px; font-weight: 500; background: var(--amber-l); border: 1px solid rgba(217,119,6,.2); color: var(--amber); }
.a-tag button { background: none; border: none; cursor: pointer; color: var(--amber); opacity: .6; font-size: 11px; }
.tag-row { display: flex; gap: 8px; }
.tag-inp { flex: 1; background: rgba(255,255,255,.8); border: 1.5px solid var(--border); border-radius: 12px; padding: 9px 13px; color: var(--ink); font-family: var(--font); font-size: 13px; outline: none; }
.tag-inp:focus { border-color: var(--amber); }
.tag-add { padding: 9px 16px; border-radius: 12px; border: none; background: var(--amber-l); color: var(--amber); font-family: var(--font); font-size: 13px; font-weight: 600; cursor: pointer; }
.mood-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 8px; margin-bottom: 12px; }
.mood-btn { display: flex; flex-direction: column; align-items: center; gap: 5px; padding: 12px 8px; border-radius: 14px; border: 1.5px solid var(--border); background: rgba(255,255,255,.7); cursor: pointer; transition: all .2s; font-size: 20px; }
.mood-btn:hover { border-color: var(--blue); transform: scale(1.05); }
.mood-btn.sel { border-color: var(--blue); background: var(--blue-g); }
.mood-lbl { font-size: 10px; color: var(--ink2); font-weight: 700; }
.mood-entry { background: rgba(26,24,20,.04); border: 1px solid var(--border); border-radius: 13px; padding: 12px 14px; margin-bottom: 8px; display: flex; gap: 10px; }
.mood-emoji { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.mood-date  { font-size: 10px; color: var(--violet); margin-bottom: 3px; font-weight: 600; }
.mood-note  { font-size: 13px; color: var(--ink); line-height: 1.5; }
.bmi-badge { margin-top: 8px; padding: 8px 12px; background: var(--blue-g); border: 1px solid rgba(37,99,235,.15); border-radius: 10px; font-size: 13px; color: var(--blue); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; z-index: 400; background: rgba(26,24,20,.4); backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; animation: fadeIn .2s ease; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
.modal { width: 100%; max-width: 420px; background: var(--paper); border: 1px solid var(--border); border-radius: var(--r-xl); padding: 36px 38px; position: relative; box-shadow: var(--shadow-lg); animation: modalIn .25s ease; }
@keyframes modalIn { from{opacity:0;transform:scale(.95) translateY(10px)} to{opacity:1;transform:none} }
.modal-title { font-size: 20px; font-weight: 600; letter-spacing: -.4px; margin-bottom: 4px; }
.modal-sub   { font-size: 13px; color: var(--ink3); margin-bottom: 24px; }
.modal-close { position: absolute; top: 16px; right: 18px; width: 28px; height: 28px; border-radius: 50%; background: rgba(26,24,20,.07); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 12px; }
.modal-divider { height: 1px; background: var(--border); margin: 20px 0; }
.modal-section { font-size: 11px; font-weight: 700; color: var(--ink3); text-transform: uppercase; letter-spacing: .09em; margin-bottom: 12px; }
.modal-btn {
  width: 100%; padding: 13px; border-radius: 980px; border: none;
  background: var(--grad-btn); background-size: 300% 100%;
  animation: shimmer 3s linear infinite;
  color: white; font-family: var(--font); font-size: 14px; font-weight: 600;
  cursor: pointer; transition: all .2s; margin-top: 6px;
  box-shadow: 0 4px 20px rgba(139,92,246,.3);
}
.modal-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(139,92,246,.5); animation-play-state: paused; }
.modal-btn.alt { background: linear-gradient(135deg,#8b5cf6,#ec4899,#8b5cf6); background-size: 300% 100%; animation: shimmer 3s linear infinite; }
.modal-btn.alt:hover { animation-play-state: paused; }
.modal-msg { font-size: 13px; text-align: center; margin-top: 10px; padding: 8px 14px; border-radius: 10px; }
.msg-ok  { color: var(--green); background: var(--green-l); }
.msg-err { color: var(--red);   background: var(--red-l); }

/* Chat */
.chat-widget { position: fixed; bottom: 24px; right: 24px; z-index: 300; display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
.chat-toggle { width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg,var(--blue),var(--violet),var(--pink)); background-size: 200% 200%; animation: gradientShift 4s ease infinite; border: none; cursor: pointer; color: white; font-size: 18px; box-shadow: 0 4px 24px rgba(139,92,246,.45); transition: all .25s; display: flex; align-items: center; justify-content: center; }
.chat-toggle:hover { transform: scale(1.08); box-shadow: 0 8px 32px rgba(26,24,20,.4); }
.chat-panel { width: 360px; height: 500px; background: var(--paper); border: 1px solid var(--border); border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; box-shadow: var(--shadow-lg); animation: panelIn .25s ease; }
@keyframes panelIn { from{opacity:0;transform:scale(.92) translateY(16px)} to{opacity:1;transform:none} }
.chat-hdr { padding: 16px 18px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 9px; }
.chat-hdr-av { width: 30px; height: 30px; border-radius: 50%; background: var(--ink); display: flex; align-items: center; justify-content: center; font-size: 13px; color: white; }
.chat-hdr-name   { font-size: 14px; font-weight: 600; }
.chat-hdr-status { font-size: 11px; color: var(--green); }
.chat-hdr-close  { margin-left: auto; width: 24px; height: 24px; border-radius: 50%; background: rgba(26,24,20,.06); border: none; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.chat-msgs { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
.chat-msg { display: flex; gap: 8px; animation: msgIn .2s ease; }
@keyframes msgIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }
.chat-msg.user { flex-direction: row-reverse; }
.chat-av { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
.chat-av-ai   { background: var(--ink); color: white; }
.chat-av-user { background: var(--blue); color: white; }
.chat-bubble { max-width: 80%; padding: 10px 13px; border-radius: 16px; font-size: 13px; line-height: 1.55; }
.bubble-ai   { background: rgba(26,24,20,.06); border: 1px solid var(--border); border-bottom-left-radius: 5px; }
.bubble-user { background: var(--ink); color: white; border-bottom-right-radius: 5px; }
.chat-typing { display: flex; gap: 4px; align-items: center; padding: 10px 13px; }
.tdot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink3); animation: blink 1.2s infinite; }
.tdot:nth-child(2){animation-delay:.2s}.tdot:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.15}40%{opacity:1}}
.chat-sugs { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 14px 10px; }
.chat-sug { font-size: 11px; padding: 5px 11px; border-radius: 20px; background: rgba(26,24,20,.06); border: 1px solid var(--border); color: var(--ink2); cursor: pointer; transition: all .15s; }
.chat-sug:hover { border-color: var(--blue); color: var(--blue); background: var(--blue-g); }
.chat-input-row { padding: 12px 14px; border-top: 1px solid var(--border); display: flex; gap: 8px; align-items: flex-end; }
.chat-in { flex: 1; background: rgba(26,24,20,.05); border: 1.5px solid var(--border); border-radius: 12px; padding: 9px 13px; color: var(--ink); font-family: var(--font); font-size: 13px; resize: none; outline: none; line-height: 1.4; max-height: 80px; transition: border-color .2s; }
.chat-in:focus { border-color: var(--blue); }
.chat-send { width: 32px; height: 32px; border-radius: 50%; border: none; background: linear-gradient(135deg,var(--blue),var(--violet)); color: white; font-size: 14px; cursor: pointer; flex-shrink: 0; transition: all .2s; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 12px rgba(139,92,246,.35); }
.chat-send:hover { background: #2d2a26; transform: scale(1.05); }
.chat-send:disabled { opacity: .35; cursor: not-allowed; transform: none; }

.no-data { background: var(--glass-hi); backdrop-filter: blur(30px); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 48px; text-align: center; color: var(--ink3); }
::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: transparent; } ::-webkit-scrollbar-thumb { background: rgba(26,24,20,.15); border-radius: 4px; }
`;

// ── Bar Chart ─────────────────────────────────────────────────────────────────
function BarChart({ data=[], color="#2563eb", h=60, expanded=false }) {
  if (!data||!data.length) return null;
  const H = expanded ? 200 : h;
  const W = 600;
  const max = Math.max(...data, .001);
  const bw  = Math.max(2, W/data.length - 1.2);
  const lblIdx = [0, Math.floor(data.length*.25), Math.floor(data.length*.5), Math.floor(data.length*.75), data.length-1];
  return (
    <div className="barchart">
      <svg viewBox={`0 0 ${W} ${H}`} className="barchart-svg" style={{height:H}}>
        {data.map((v,i)=>{
          const bh = Math.max(2,(v/max)*(H-4));
          return <rect key={i} x={i*(W/data.length)} y={H-bh} width={bw} height={bh} fill={color} opacity={v>0?.8:.1} rx="2"/>;
        })}
        <line x1="0" y1={H*.25} x2={W} y2={H*.25} stroke={color} strokeWidth=".5" strokeDasharray="4 4" opacity=".3"/>
      </svg>
      <div className="time-labels">
        {lblIdx.map((idx,i)=><span key={i} className="time-lbl">{["00:00","06:00","12:00","18:00","24:00"][i]}</span>)}
      </div>
    </div>
  );
}

// ── Activity Card ─────────────────────────────────────────────────────────────
function ACard({ name, val, unit, sub, data, color, accentClass }) {
  const [exp, setExp] = useState(false);
  const has = data&&data.length>0;
  const nz  = has ? data.filter(v=>v>0) : [];
  const peak  = has ? Math.max(...data).toFixed(1) : "—";
  const avg   = nz.length ? (nz.reduce((a,b)=>a+b,0)/nz.length).toFixed(1) : "—";
  const total = has ? data.reduce((a,b)=>a+b,0).toFixed(1) : "—";
  return (
    <>
      {exp && <div className="ac-overlay" onClick={()=>setExp(false)}/>}
      <div className={`ac-card${exp?" expanded":""}`} onClick={()=>!exp&&has&&setExp(true)}
        style={exp?{height:"auto",alignSelf:"flex-start"}:{}}>
        {accentClass && <div className={`gc-accent ${accentClass}`}/>}
        {exp && <button className="ac-close" onClick={e=>{e.stopPropagation();setExp(false);}}>✕</button>}
        <div className="ac-name">{name}</div>
        <div className="ac-val" style={{color}}>{val}<span className="ac-unit">{unit}</span></div>
        {sub && <div className="ac-sub" style={{color}}>{sub}</div>}
        {has && <BarChart data={data} color={color} h={exp?180:60} expanded={exp}/>}
        {exp && has && (
          <div className="ac-stats">
            {[["Average",avg,unit],["Peak",peak,unit],["Total",total,unit]].map(([l,v,u])=>(
              <div className="ac-stat" key={l}>
                <div className="ac-stat-l">{l}</div>
                <div className="ac-stat-v" style={{color}}>{v} <span style={{fontSize:14,color:"var(--ink3)"}}>{u}</span></div>
              </div>
            ))}
          </div>
        )}
        {!exp && has && <div className="hint">Tap to expand ↗</div>}
      </div>
    </>
  );
}

// ── Rings ─────────────────────────────────────────────────────────────────────
function Rings({ move=0, exercise=0, stand=0 }) {
  const rows=[
    {label:"Move",     pct:move,     color:"#ef4444"},
    {label:"Exercise", pct:exercise, color:"#16a34a"},
    {label:"Stand",    pct:stand,    color:"#2563eb"},
  ];
  const cx=56, cy=56;
  const rs=[48,36,24];
  return (
    <div style={{display:"flex",alignItems:"center",gap:24}}>
      <svg viewBox="0 0 112 112" style={{width:110,height:110,flexShrink:0}}>
        {rows.map(({color,pct},i)=>{
          const r=rs[i], c=2*Math.PI*r, d=(Math.min(pct,100)/100)*c;
          return (<g key={i}>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="8" opacity=".12"/>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
              strokeDasharray={`${d} ${c}`} style={{transformOrigin:`${cx}px ${cy}px`,transform:"rotate(-90deg)",transition:"stroke-dasharray 1.2s"}}/>
          </g>);
        })}
      </svg>
      <div style={{flex:1}}>
        {rows.map(({label,pct,color})=>(
          <div className="ring-row" key={label}>
            <div className="ring-dot" style={{background:color}}/>
            <div className="ring-lbl">{label}</div>
            <div className="ring-bar"><div className="ring-fill" style={{width:`${Math.min(pct,100)}%`,background:color}}/></div>
            <div className="ring-pct" style={{color}}>{pct}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Auth ──────────────────────────────────────────────────────────────────────
function AuthPage({ onAuth }) {
  const [view,setView]         = useState("login");
  const [name,setName]         = useState("");
  const [email,setEmail]       = useState("");
  const [password,setPassword] = useState("");
  const [loading,setLoading]   = useState(false);
  const [error,setError]       = useState("");
  const submit = async e => {
    e.preventDefault(); setLoading(true); setError("");
    const ep = view==="login"?"login":"register";
    const body = view==="login"?{email,password}:{name,email,password};
    try {
      const res=await fetch(`${API}/auth/${ep}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      const data=await res.json();
      if(!res.ok) throw new Error(data.detail||"Failed");
      saveAuth(data.token,{user_id:data.user_id,email:data.email,name:data.name});
      onAuth(data);
    } catch(e){setError(e.message);}
    finally{setLoading(false);}
  };
  return (
    <>
      <style>{css}</style>
      <div className="auth-page">
        <div className="auth-left">
          <div className="auth-logo-dark">
            <div className="auth-logo-dot">♥</div>
            <div className="auth-logo-name">HealthPlatform</div>
          </div>
          <div className="auth-tagline">Take care of<br/>your <em>health</em></div>
          <div className="auth-desc">AI-powered health analytics from your Apple Watch. Upload your data and get personalised insights in seconds.</div>
          <div className="auth-stats">
            {[["88.4%","Model accuracy"],["2M+","Records processed"],["120 days","Data window"],["GPT-4o","AI assistant"]].map(([v,l])=>(
              <div className="auth-stat" key={l}><div className="auth-stat-val">{v}</div><div className="auth-stat-lbl">{l}</div></div>
            ))}
          </div>
        </div>
        <div className="auth-right">
          <div className="auth-card">
            <div className="auth-card-title">{view==="login"?"Welcome back":"Create account"}</div>
            <div className="auth-card-sub">{view==="login"?"Sign in to your account":"Start analysing your Apple Watch data"}</div>
            <form onSubmit={submit}>
              {view==="register"&&<div className="field"><label>Name</label><input type="text" placeholder="Nataliia" value={name} onChange={e=>setName(e.target.value)} required/></div>}
              <div className="field"><label>Email</label><input type="email" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)} required/></div>
              <div className="field"><label>Password</label><input type="password" placeholder="••••••••" value={password} onChange={e=>setPassword(e.target.value)} required minLength={6}/></div>
              {error&&<div className="auth-err">{error}</div>}
              <button className="auth-btn" type="submit" disabled={loading}>{loading?(view==="login"?"Signing in…":"Creating…"):(view==="login"?"Sign in →":"Create account →")}</button>
            </form>
            <div className="auth-switch">
              {view==="login"?"No account? ":"Have an account? "}
              <button className="auth-link" onClick={()=>{setView(v=>v==="login"?"register":"login");setError("");}}>
                {view==="login"?"Create one":"Sign in"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Account Modal ─────────────────────────────────────────────────────────────
function AccountModal({ user, onClose, onUpdated, onLogout }) {
  const [name,setName]           = useState(user.name||"");
  const [email,setEmail]         = useState(user.email||"");
  const [currPass,setCurrPass]   = useState("");
  const [newPass,setNewPass]     = useState("");
  const [confPass,setConfPass]   = useState("");
  const [loading,setLoading]     = useState(false);
  const [msg,setMsg]             = useState(null);

  const saveProf = async () => {
    setLoading(true); setMsg(null);
    try {
      const res=await fetch(`${API}/auth/update`,{method:"PATCH",headers:authHdr(),body:JSON.stringify({name,email})});
      const updated={...user,name,email};
      localStorage.setItem("hp_user",JSON.stringify(updated));
      onUpdated(updated); setMsg({t:"Profile saved!",ok:true});
    } catch { const up={...user,name,email}; localStorage.setItem("hp_user",JSON.stringify(up)); onUpdated(up); setMsg({t:"Saved locally",ok:true}); }
    finally{setLoading(false);}
  };
  const changePass = async () => {
    if(!currPass||!newPass){setMsg({t:"Fill both fields",ok:false});return;}
    if(newPass.length<6){setMsg({t:"Min 6 characters",ok:false});return;}
    if(newPass!==confPass){setMsg({t:"Passwords don't match",ok:false});return;}
    setLoading(true); setMsg(null);
    try {
      const res=await fetch(`${API}/auth/change-password`,{method:"POST",headers:authHdr(),body:JSON.stringify({current_password:currPass,new_password:newPass})});
      if(res.ok){setMsg({t:"Password changed!",ok:true});setCurrPass("");setNewPass("");setConfPass("");}
      else{const e=await res.json();setMsg({t:e.detail||"Wrong current password",ok:false});}
    } catch{setMsg({t:"Server unavailable",ok:false});}
    finally{setLoading(false);}
  };
  return (
    <div className="modal-overlay" onClick={e=>e.target===e.currentTarget&&onClose()}>
      <div className="modal">
        <button className="modal-close" onClick={onClose}>✕</button>
        <div className="modal-title">Account settings</div>
        <div className="modal-sub">Update your name, email or password</div>
        <div className="modal-section">Profile</div>
        <div className="field" style={{marginBottom:10}}><label>Name</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="Your name"/></div>
        <div className="field" style={{marginBottom:6}}><label>Email</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)}/></div>
        <button className="modal-btn" onClick={saveProf} disabled={loading}>Save profile</button>
        <div className="modal-divider"/>
        <div className="modal-section">Change password</div>
        <div className="field" style={{marginBottom:10}}><label>Current password</label><input type="password" placeholder="••••••••" value={currPass} onChange={e=>setCurrPass(e.target.value)}/></div>
        <div className="field" style={{marginBottom:10}}><label>New password</label><input type="password" placeholder="min. 6 chars" value={newPass} onChange={e=>setNewPass(e.target.value)}/></div>
        <div className="field" style={{marginBottom:6}}><label>Confirm</label><input type="password" placeholder="••••••••" value={confPass} onChange={e=>setConfPass(e.target.value)} onKeyDown={e=>e.key==="Enter"&&changePass()}/></div>
        <button className="modal-btn alt" onClick={changePass} disabled={loading}>Change password</button>
        {msg&&<div className={`modal-msg ${msg.ok?"msg-ok":"msg-err"}`}>{msg.t}</div>}

        <div className="modal-divider"/>

        <button
          onClick={()=>{ onClose(); onLogout(); }}
          style={{
            width:"100%", padding:"12px", borderRadius:980, border:"1.5px solid",
            borderColor:"rgba(239,68,68,.25)", background:"rgba(239,68,68,.06)",
            color:"#dc2626", fontFamily:"var(--font)", fontSize:14, fontWeight:600,
            cursor:"pointer", transition:"all .2s", display:"flex",
            alignItems:"center", justifyContent:"center", gap:8,
          }}
          onMouseEnter={e=>{e.currentTarget.style.background="rgba(239,68,68,.12)";e.currentTarget.style.borderColor="rgba(239,68,68,.4)";}}
          onMouseLeave={e=>{e.currentTarget.style.background="rgba(239,68,68,.06)";e.currentTarget.style.borderColor="rgba(239,68,68,.25)";}}
        >
          <span style={{fontSize:16}}>→</span> Sign out
        </button>
      </div>
    </div>
  );
}

// ── Chat Widget ───────────────────────────────────────────────────────────────
function ChatWidget({ uploadData }) {
  const [open,setOpen]=useState(false);
  const [msgs,setMsgs]=useState([{role:"ai",text:"Hi! I can see your health data. Ask me about your heart rate, activity, or what your AI predictions mean."}]);
  const [input,setInput]=useState(""); const [typing,setTyping]=useState(false);
  const bottomRef=useRef(); const userId=uploadData?.user_id??"demo";
  useEffect(()=>{bottomRef.current?.scrollIntoView({behavior:"smooth"});},[msgs,typing]);
  const send=async()=>{
    const msg=input.trim(); if(!msg) return;
    setInput(""); setMsgs(p=>[...p,{role:"user",text:msg}]); setTyping(true);
    try{
      const profile=getProfile();
      const ctx=profile.moodLogs?.[0]?`Latest mood: ${profile.moodLogs[0].emoji} — "${profile.moodLogs[0].note}". `:"";
      const res=await fetch(`${API}/chat`,{method:"POST",headers:authHdr(),body:JSON.stringify({user_id:userId,message:ctx+msg,stats:uploadData?.stats??null,inject_context:msgs.length<=1})});
      const data=await res.json();
      setMsgs(p=>[...p,{role:"ai",text:data.reply??data.detail??"Something went wrong."}]);
    }catch{setMsgs(p=>[...p,{role:"ai",text:"Could not reach the server."}]);}
    finally{setTyping(false);}
  };
  const onKey=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}};
  const sugs=["What does my prediction mean?","Is my HR normal?","Give me a health tip","Am I active enough?"];
  return (
    <div className="chat-widget">
      {open&&(
        <div className="chat-panel">
          <div className="chat-hdr">
            <div className="chat-hdr-av">🤖</div>
            <div><div className="chat-hdr-name">Health AI</div><div className="chat-hdr-status">● Online · GPT-4o</div></div>
            <button className="chat-hdr-close" onClick={()=>setOpen(false)}>✕</button>
          </div>
          <div className="chat-msgs">
            {msgs.map((m,i)=>(
              <div className={`chat-msg${m.role==="user"?" user":""}`} key={i}>
                <div className={`chat-av ${m.role==="user"?"chat-av-user":"chat-av-ai"}`}>{m.role==="user"?"U":"AI"}</div>
                <div className={`chat-bubble ${m.role==="user"?"bubble-user":"bubble-ai"}`}>{m.text}</div>
              </div>
            ))}
            {typing&&<div className="chat-msg"><div className="chat-av chat-av-ai">AI</div><div className="chat-bubble bubble-ai"><div className="chat-typing"><div className="tdot"/><div className="tdot"/><div className="tdot"/></div></div></div>}
            <div ref={bottomRef}/>
          </div>
          {msgs.length<=1&&<div className="chat-sugs">{sugs.map(s=><button key={s} className="chat-sug" onClick={()=>setInput(s)}>{s}</button>)}</div>}
          <div className="chat-input-row">
            <textarea className="chat-in" rows={1} placeholder="Ask about your health…" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={onKey}/>
            <button className="chat-send" onClick={send} disabled={!input.trim()||typing}>↑</button>
          </div>
        </div>
      )}
      <button className="chat-toggle" onClick={()=>setOpen(o=>!o)}>💬</button>
    </div>
  );
}

// ── Upload Page ───────────────────────────────────────────────────────────────
function UploadPage({ onUploaded }) {
  const [drag,setDrag]=useState(false); const [file,setFile]=useState(null);
  const [loading,setLoading]=useState(false); const [progress,setProgress]=useState(0);
  const [error,setError]=useState(""); const inputRef=useRef();
  const handleFile=f=>{if(f){setFile(f);setError("");}};
  const upload=async()=>{
    if(!file) return; setLoading(true); setProgress(15);
    try{
      const fd=new FormData(); fd.append("file",file); setProgress(45);
      const res=await fetch(`${API}/upload`,{method:"POST",headers:{"Authorization":`Bearer ${getToken()}`},body:fd});
      setProgress(85);
      if(!res.ok){const e=await res.json();throw new Error(e.detail||`Error ${res.status}`);}
      const data=await res.json(); setProgress(100);
      setTimeout(()=>onUploaded(data),400);
    }catch(e){setError(e.message);setProgress(0);}
    finally{setLoading(false);}
  };
  return (
    <div className="page">
      <div className="page-hdr"><div><div className="page-title">Import data</div><div className="page-sub">Upload your Apple Health export to begin</div></div></div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20,marginBottom:24}}>
        <div>
          <div className={`upload-zone${drag?" drag":""}`}
            onClick={()=>inputRef.current?.click()}
            onDragOver={e=>{e.preventDefault();setDrag(true);}}
            onDragLeave={()=>setDrag(false)}
            onDrop={e=>{e.preventDefault();setDrag(false);handleFile(e.dataTransfer.files[0]);}}>
            <input ref={inputRef} type="file" accept=".xml,.csv" style={{display:"none"}} onChange={e=>handleFile(e.target.files[0])}/>
            <div className="upload-glyph">⬆</div>
            <div className="upload-title">{file?file.name:"Drop your export here"}</div>
            <div className="upload-sub">{file?<><em>{(file.size/1_048_576).toFixed(1)} MB</em> — ready to analyse</>:<>Apple Health <em>export.xml</em> or health CSV</>}</div>
          </div>
          {progress>0&&<div className="progress-track"><div className="progress-fill" style={{width:`${progress}%`}}/></div>}
          {error&&<div style={{marginTop:10,fontSize:13,color:"var(--red)",lineHeight:1.5}}>{error}</div>}
          <div style={{display:"flex",gap:10,marginTop:18}}>
            <button className="btn btn-dark" disabled={!file||loading} onClick={upload}>{loading?"Analysing…":"Analyse data →"}</button>
            {file&&<button className="btn btn-ghost btn-sm" onClick={()=>{setFile(null);setProgress(0);setError("");}}>Clear</button>}
          </div>
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          <div style={{fontSize:10,color:"var(--ink3)",fontWeight:700,textTransform:"uppercase",letterSpacing:".1em",marginBottom:4}}>Supported formats</div>
          {[{icon:"🍎",bg:"#fee2e2",name:"export.xml",desc:"Full Apple Health — all metrics"},{icon:"📋",bg:"#dbeafe",name:"export_cda.xml",desc:"CDA/HL7 clinical format"},{icon:"📊",bg:"#dcfce7",name:"Health CSV",desc:"Any smartwatch with health columns"}].map(f=>(
            <div className="fmt-item" key={f.name}><div className="fmt-icon" style={{background:f.bg}}>{f.icon}</div><div><div className="fmt-name">{f.name}</div><div className="fmt-desc">{f.desc}</div></div></div>
          ))}
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:14}}>
        {[{bg:"#dbeafe",icon:"⚡",t:"Streaming parser",d:"Handles Apple Health files up to 800 MB without memory issues"},{bg:"#dcfce7",icon:"✦",t:"Smart pipeline",d:"Auto-detects columns, fills gaps, normalises units"},{bg:"#ede9fe",icon:"◎",t:"Hybrid ML",d:"LSTM + XGBoost — 88.4% accuracy on real Apple Watch data"}].map(c=>(
          <div key={c.t} style={{background:"var(--glass-hi)",backdropFilter:"blur(30px)",border:"1px solid var(--border)",borderRadius:"var(--r-lg)",padding:22,boxShadow:"var(--shadow)"}}>
            <div style={{width:40,height:40,borderRadius:12,background:c.bg,display:"flex",alignItems:"center",justifyContent:"center",fontSize:20,marginBottom:12}}>{c.icon}</div>
            <div style={{fontSize:15,fontWeight:600,marginBottom:5}}>{c.t}</div>
            <div style={{fontSize:13,color:"var(--ink2)",lineHeight:1.55}}>{c.d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
function DashboardPage({ uploadData }) {
  const [predict,setPredict]=useState(null); const [analysis,setAnalysis]=useState(null);
  const userId=uploadData?.user_id??"demo";
  const load=async()=>{
    try{
      const [aR,pR]=await Promise.all([
        fetch(`${API}/analysis/${userId}`,{headers:authHdr()}),
        fetch(`${API}/predict/${userId}`,{method:"POST",headers:authHdr()}),
      ]);
      if(aR.ok) setAnalysis(await aR.json());
      if(pR.ok) setPredict(await pR.json());
    }catch{}
  };
  useEffect(()=>{load();},[]);
  const stats=analysis?.stats??uploadData?.stats??{};
  const charts=analysis?.charts??{};
  const rows=uploadData?.rows??0;
  const profile=getProfile();
  const ds={...stats};
  if(profile.weight&&parseFloat(profile.weight)>0){
    ds.avg_weight=parseFloat(profile.weight);
    if(profile.height&&parseFloat(profile.height)>0) ds.avg_bmi=Math.round(parseFloat(profile.weight)/Math.pow(parseFloat(profile.height)/100,2)*10)/10;
  }
  const hr=charts.heart_rate??[]; const ae=charts.active_energy??[]; const st=charts.steps??[];
  const moveV =ae.length?Math.min(100,Math.round((ae.filter(v=>v>0).length/ae.length)*140)):0;
  const exerV =st.length?Math.min(100,Math.round((st.filter(v=>v>500).length/st.length)*200)):0;
  const standV=hr.length?Math.min(100,Math.round((hr.filter(v=>v>60&&v<120).length/hr.length)*110)):0;
  const hasAny=hr.length||ae.length||st.length||charts.distance?.length;

  const pc=l=>{const s=(l||"").toLowerCase();if(s.includes("high")||s.includes("vigor"))return "pp-high";if(s.includes("med")||s.includes("light")||s.includes("active"))return "pp-medium";return "pp-gray";};
  const bc=l=>{const s=(l||"").toLowerCase();if(s.includes("high")||s.includes("vigor"))return "#ef4444";if(s.includes("med")||s.includes("light")||s.includes("active"))return "#16a34a";return "#2563eb";};

  return (
    <div className="page">
      <div className="page-hdr">
        <div><div className="page-title">Your health</div><div className="page-sub">{rows>0?`${rows.toLocaleString()} hourly records · last 120 days`:"Upload a file to see your data"}</div></div>
        <button className="btn btn-ghost btn-sm" onClick={load} style={{marginTop:4}}>↻ Refresh</button>
      </div>

      {/* Prediction hero */}
      <div className="pred-hero" style={{marginBottom:14}}>
        <div className="pred-tag">🧠 ML Prediction · LSTM + XGBoost Hybrid</div>
        <div className="pred-title">What is your current activity level?</div>
        <div className="pred-desc">
          <b style={{color:"#93c5fd"}}>XGBoost</b> classifies your current state from the latest data.
          <b style={{color:"#c4b5fd"}}> LSTM</b> looks at the past 30 hours to forecast the next.
          The <b style={{color:"white"}}>Hybrid</b> (70% XGB + 30% LSTM) gives the most reliable estimate.
        </div>
        {predict?(
          <div className="pred-models">
            {[{l:"XGB · Right now",v:predict.current,c:predict.confidence?.xgb,tip:"Instant snapshot"},{l:"LSTM · Next hour",v:predict.next,c:predict.confidence?.lstm,tip:"Time-series forecast"},{l:"Hybrid · Best estimate",v:predict.hybrid,c:predict.confidence?.hybrid,tip:"70% XGB + 30% LSTM"}].map(p=>(
              <div className="pred-card" key={p.l}>
                <div className="pred-card-lbl">{p.l}</div>
                <div className={`pred-pill ${pc(p.v)}`}>{p.v}</div>
                {p.c&&<><div className="pred-bar"><div className="pred-fill" style={{width:`${p.c*100}%`,background:bc(p.v)}}/></div><div className="pred-conf">{(p.c*100).toFixed(0)}% confidence · {p.tip}</div></>}
              </div>
            ))}
          </div>
        ):<div style={{color:"rgba(255,255,255,.4)",fontSize:14}}>Upload a file to see predictions</div>}
      </div>

      {/* ── ROW 1: Key metrics ── */}
      <div className="bento" style={{marginBottom:12}}>
        {ds.avg_hr!=null&&(
          <div className="gc b-3">
            <div className="gc-accent ac-red"/>
            <div className="card-label">Avg heart rate</div>
            <div className="card-val" style={{color:"var(--red)"}}>{ds.avg_hr.toFixed(0)}<span className="card-unit"> bpm</span></div>
            {ds.min_hr&&<div className="card-sub">Range {ds.min_hr}–{ds.max_hr}</div>}
            <div className="card-tag tag-red">Cardio</div>
          </div>
        )}
        {ds.avg_weight!=null&&(
          <div className="gc b-3">
            <div className="gc-accent ac-blue"/>
            <div className="card-label">Weight</div>
            <div className="card-val" style={{color:"var(--blue)"}}>{ds.avg_weight.toFixed(1)}<span className="card-unit"> kg</span></div>
            <div className="card-tag tag-blue">Body</div>
          </div>
        )}
        {ds.avg_active_energy!=null&&(
          <div className="gc b-3">
            <div className="gc-accent ac-amber"/>
            <div className="card-label">Active energy</div>
            <div className="card-val" style={{color:"var(--amber)"}}>{ds.avg_active_energy.toFixed(0)}<span className="card-unit"> kcal/h</span></div>
            <div className="card-tag tag-amber">Move</div>
          </div>
        )}
        {ds.dominant_sleep&&(
          <div className="gc b-3">
            <div className="gc-accent ac-violet"/>
            <div className="card-label">Sleep stage</div>
            <div className="card-val" style={{color:"var(--violet)",fontSize:28}}>{ds.dominant_sleep}</div>
            <div className="card-tag tag-violet">Sleep</div>
          </div>
        )}
      </div>

      {/* ── ROW 2: BMI + Activity Rings ── */}
      <div className="bento" style={{marginBottom:12}}>
        {ds.avg_bmi!=null&&(
          <div className="gc b-4">
            <div className="gc-accent" style={{background:"linear-gradient(90deg,#34d399,#6ee7b7)"}}/>
            <div className="card-label">Body Mass Index</div>
            <div style={{display:"flex",alignItems:"flex-end",gap:10,marginBottom:10}}>
              <div className="card-val" style={{color:"#059669",fontSize:46,lineHeight:1}}>{ds.avg_bmi}</div>
              <div style={{marginBottom:6}}>
                <div style={{
                  fontSize:12,fontWeight:700,padding:"3px 10px",borderRadius:20,
                  background:ds.avg_bmi<18.5?"#fef3c7":ds.avg_bmi<25?"#d1fae5":ds.avg_bmi<30?"#fed7aa":"#fee2e2",
                  color:ds.avg_bmi<18.5?"#d97706":ds.avg_bmi<25?"#059669":ds.avg_bmi<30?"#ea580c":"#dc2626",
                }}>
                  {ds.avg_bmi<18.5?"Underweight":ds.avg_bmi<25?"Normal weight":ds.avg_bmi<30?"Overweight":"Obese"}
                </div>
              </div>
            </div>
            <div style={{height:6,borderRadius:4,background:"linear-gradient(90deg,#60a5fa 0%,#34d399 30%,#fbbf24 60%,#f87171 100%)",marginBottom:6,position:"relative"}}>
              <div style={{position:"absolute",top:-3,left:`${Math.min(Math.max((ds.avg_bmi-10)/30*100,2),97)}%`,width:12,height:12,borderRadius:"50%",background:"white",border:"2.5px solid #6366f1",transform:"translateX(-50%)",boxShadow:"0 1px 6px rgba(0,0,0,.2)"}}/>
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:9,color:"var(--ink3)",fontWeight:600}}>
              <span>10</span><span>18.5</span><span>25</span><span>30</span><span>40</span>
            </div>
          </div>
        )}
        {(moveV>0||exerV>0||standV>0)&&(
          <div className="gc" style={{gridColumn:`span ${ds.avg_bmi!=null?8:12}`}}>
            <div className="card-label">Activity rings · today</div>
            <div style={{marginTop:12}}><Rings move={moveV} exercise={exerV} stand={standV}/></div>
          </div>
        )}
      </div>

      {/* ── ROW 3: Charts ── */}
      {hasAny&&<div style={{fontSize:10,fontWeight:700,color:"var(--ink3)",textTransform:"uppercase",letterSpacing:".1em",marginBottom:10}}>Activity charts · tap any to expand</div>}
      <div className="bento" style={{marginBottom:12}}>
        {hr.length>0&&(
          <div className="b-6">
            <ACard name="Heart Rate" val={ds.avg_hr?.toFixed(0)??"—"} unit=" bpm"
              sub={ds.min_hr?`Range ${ds.min_hr}–${ds.max_hr} bpm`:null}
              data={hr} color="var(--red)" accentClass="ac-red"/>
          </div>
        )}
        {ae.length>0&&(
          <div className="b-6">
            <ACard name="Active Energy" val={ds.avg_active_energy?.toFixed(0)??"—"} unit=" kcal"
              sub="Average per hour" data={ae} color="var(--amber)" accentClass="ac-amber"/>
          </div>
        )}
        {st.length>0&&(
          <div className="b-6">
            <ACard name="Steps" val={st.length?(st.reduce((a,b)=>a+b,0)/st.length).toFixed(0):"—"} unit=" /hr"
              sub="Tap to expand" data={st} color="var(--green)" accentClass="ac-green"/>
          </div>
        )}
        {charts.distance?.length>0&&(
          <div className="b-6">
            <ACard name="Distance" val={charts.distance.reduce((a,b)=>a+b,0).toFixed(1)} unit=" km"
              sub="Walking + running" data={charts.distance} color="var(--blue)" accentClass="ac-blue"/>
          </div>
        )}
      </div>

      {/* ── ROW 4: Insights ── */}
      {hasAny&&(
        <div className="bento" style={{marginBottom:0}}>
          {[
            {icon:"💤",t:"Sleep insight",bg:"var(--violet-l)",c:"var(--violet)",
             d:ds.dominant_sleep?`Dominant stage: ${ds.dominant_sleep}. Consistent deep sleep improves recovery and reduces resting heart rate.`:"Upload export.xml to unlock sleep stage analysis."},
            {icon:"❤️",t:"Heart rate zone",bg:"var(--red-l)",c:"var(--red)",
             d:ds.avg_hr?ds.avg_hr<60?"Excellent resting zone — athletes typically stay below 60 bpm.":ds.avg_hr<80?"Healthy range. Aim for 30 min cardio daily.":"Slightly elevated. Try breathing exercises or a brisk walk.":"Load data to see heart rate analysis."},
            {icon:"🔥",t:"Calorie tip",bg:"var(--amber-l)",c:"var(--amber)",
             d:ds.avg_active_energy?ds.avg_active_energy>200?`Burning ${ds.avg_active_energy.toFixed(0)} kcal/hr — great output! Fuel recovery well.`:`Burning ${ds.avg_active_energy.toFixed(0)} kcal/hr. A 20-min walk boosts your daily total.`:"Upload data to see calorie insights."},
          ].map(c=>(
            <div className="insight-card b-4" key={c.t} style={{borderTop:`3px solid ${c.c}`,background:`linear-gradient(160deg,${c.bg}40,var(--glass-hi) 50%)`}}>
              <div className="insight-icon">{c.icon}</div>
              <div className="insight-title">{c.t}</div>
              <div className="insight-text">{c.d}</div>
            </div>
          ))}
        </div>
      )}

      {!hasAny&&(
        <div className="no-data">
          <div style={{fontSize:36,marginBottom:12}}>📊</div>
          <div style={{fontSize:16,fontWeight:600,marginBottom:6}}>No chart data yet</div>
          <div style={{fontSize:13,color:"var(--ink3)"}}>Upload export.xml for steps, sleep, calories and more</div>
        </div>
      )}
    </div>
  );
}

// ── Profile Page ──────────────────────────────────────────────────────────────
function ProfilePage() {
  const init=getProfile();
  const [weight,setWeight]=useState(init.weight||""); const [height,setHeight]=useState(init.height||"");
  const [age,setAge]=useState(init.age||""); const [bloodType,setBloodType]=useState(init.bloodType||"");
  const [goal,setGoal]=useState(init.goal||""); const [moveGoal,setMoveGoal]=useState(init.moveGoal||"500");
  const [exerciseGoal,setExerciseGoal]=useState(init.exerciseGoal||"30");
  const [allergies,setAllergies]=useState(init.allergies||[]); const [aInp,setAInp]=useState("");
  const [moodLogs,setMoodLogs]=useState(init.moodLogs||[]); const [selMood,setSelMood]=useState("");
  const [moodNote,setMoodNote]=useState(""); const [saved,setSaved]=useState(false);
  const GOALS=[{id:"lose",icon:"🔥",l:"Lose weight",d:"Calorie deficit & cardio"},{id:"gain",icon:"💪",l:"Build muscle",d:"Strength & protein"},{id:"maintain",icon:"⚖️",l:"Stay healthy",d:"Balanced activity"},{id:"endurance",icon:"🏃",l:"Endurance",d:"Cardio & stamina"}];
  const MOODS=[{e:"😄",l:"Great"},{e:"🙂",l:"Good"},{e:"😐",l:"Okay"},{e:"😔",l:"Low"},{e:"😩",l:"Rough"}];
  const addAllergy=()=>{if(!aInp.trim())return;setAllergies(a=>[...a,aInp.trim()]);setAInp("");};
  const logMood=()=>{
    if(!selMood)return;
    setMoodLogs(l=>[{emoji:selMood,note:moodNote,date:new Date().toLocaleString("en-US",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})},...l].slice(0,20));
    setSelMood("");setMoodNote("");
  };
  const save=()=>{saveProfile({weight,height,age,bloodType,goal,moveGoal,exerciseGoal,allergies,moodLogs});setSaved(true);setTimeout(()=>setSaved(false),2500);};
  const bmi=weight&&height?Math.round(parseFloat(weight)/Math.pow(parseFloat(height)/100,2)*10)/10:null;
  const bmiLabel=bmi?(bmi<18.5?"Underweight":bmi<25?"Normal weight":bmi<30?"Overweight":"Obese"):"";
  return (
    <div className="page">
      <div className="page-hdr">
        <div><div className="page-title">My Profile</div><div className="page-sub">Personal data, goals & wellness journal</div></div>
        <div style={{display:"flex",alignItems:"center",marginTop:4}}>
          <button className="save-btn" onClick={save}>Save all</button>
          {saved&&<span className="save-toast">✓ Saved</span>}
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        {/* Body metrics */}
        <div className="prof-section">
          <div className="ps-title">📏 Body metrics</div>
          <div className="pf-row"><div className="pf"><label>Weight (kg)</label><input type="number" placeholder="65" value={weight} onChange={e=>setWeight(e.target.value)}/></div><div className="pf"><label>Height (cm)</label><input type="number" placeholder="170" value={height} onChange={e=>setHeight(e.target.value)}/></div></div>
          <div className="pf-row"><div className="pf"><label>Age</label><input type="number" placeholder="25" value={age} onChange={e=>setAge(e.target.value)}/></div><div className="pf"><label>Blood type</label><select value={bloodType} onChange={e=>setBloodType(e.target.value)}><option value="">Select…</option>{["A+","A−","B+","B−","AB+","AB−","O+","O−"].map(t=><option key={t}>{t}</option>)}</select></div></div>
          {bmi&&<div className="bmi-badge">BMI: <b>{bmi}</b> · {bmiLabel}</div>}
        </div>
        {/* Activity goals */}
        <div className="prof-section">
          <div className="ps-title">🎯 Daily goals</div>
          <div className="pf-row"><div className="pf"><label>Move goal (kcal)</label><input type="number" value={moveGoal} onChange={e=>setMoveGoal(e.target.value)}/></div><div className="pf"><label>Exercise (min)</label><input type="number" value={exerciseGoal} onChange={e=>setExerciseGoal(e.target.value)}/></div></div>
          <div style={{marginTop:4}}>
            <label style={{display:"block",fontSize:11,fontWeight:600,color:"var(--ink3)",marginBottom:10,textTransform:"uppercase",letterSpacing:".07em"}}>Fitness goal</label>
            {GOALS.map(g=>(
              <div key={g.id} className={`goal-opt${goal===g.id?" sel":""}`} onClick={()=>setGoal(g.id)}>
                <span style={{fontSize:18}}>{g.icon}</span>
                <div><div style={{fontSize:14,fontWeight:500}}>{g.l}</div><div style={{fontSize:11,color:"var(--ink3)"}}>{g.d}</div></div>
                <div className="goal-radio"/>
              </div>
            ))}
          </div>
        </div>
        {/* Allergies */}
        <div className="prof-section">
          <div className="ps-title">⚠️ Allergies</div>
          <div className="allergy-tags">{allergies.length?allergies.map((a,i)=><div className="a-tag" key={i}>{a}<button onClick={()=>setAllergies(al=>al.filter((_,j)=>j!==i))}>✕</button></div>):<span style={{fontSize:13,color:"var(--ink3)"}}>None added</span>}</div>
          <div className="tag-row"><input className="tag-inp" placeholder="e.g. Gluten, Nuts…" value={aInp} onChange={e=>setAInp(e.target.value)} onKeyDown={e=>e.key==="Enter"&&addAllergy()}/><button className="tag-add" onClick={addAllergy}>+ Add</button></div>
        </div>
        {/* Health notes */}
        <div className="prof-section">
          <div className="ps-title">📋 Health notes</div>
          <div className="pf"><label>Conditions / medications</label><textarea placeholder="Anything your AI assistant should know…" defaultValue={init.healthNotes||""} onChange={e=>{const p=getProfile();saveProfile({...p,healthNotes:e.target.value});}}/></div>
        </div>
        {/* Emotional journal — full width */}
        <div className="prof-section" style={{gridColumn:"1/-1"}}>
          <div className="ps-title">💭 Emotional wellness journal</div>
          <label style={{display:"block",fontSize:11,fontWeight:600,color:"var(--ink3)",marginBottom:10,textTransform:"uppercase",letterSpacing:".07em"}}>How are you feeling?</label>
          <div className="mood-grid">{MOODS.map(m=><div key={m.e} className={`mood-btn${selMood===m.e?" sel":""}`} onClick={()=>setSelMood(m.e)}>{m.e}<span className="mood-lbl">{m.l}</span></div>)}</div>
          <div className="pf" style={{marginBottom:10}}><textarea placeholder="Write about your day, energy, emotions… your AI reads this for better advice." value={moodNote} onChange={e=>setMoodNote(e.target.value)} style={{minHeight:70}}/></div>
          <button className="save-btn" onClick={logMood} disabled={!selMood} style={{padding:"9px 20px",fontSize:13}}>Log entry</button>
          {moodLogs.length>0&&(
            <div style={{marginTop:20}}>
              <div style={{fontSize:11,fontWeight:700,color:"var(--ink3)",textTransform:"uppercase",letterSpacing:".08em",marginBottom:10}}>Recent entries</div>
              {moodLogs.slice(0,5).map((log,i)=>(
                <div className="mood-entry" key={i}>
                  <div className="mood-emoji">{log.emoji}</div>
                  <div><div className="mood-date">{log.date}</div><div className="mood-note">{log.note||"No note"}</div></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Tips Page ─────────────────────────────────────────────────────────────────
function TipsPage({ uploadData }) {
  const profile = getProfile();
  const stats   = uploadData?.stats ?? {};
  const [done, setDone] = useState(() => {
    try { return JSON.parse(localStorage.getItem("hp_tips_done")||"{}"); } catch { return {}; }
  });
  const [expanded, setExpanded] = useState(null);

  const toggle = id => {
    const next = {...done, [id]: !done[id]};
    setDone(next);
    localStorage.setItem("hp_tips_done", JSON.stringify(next));
  };

  const goal = profile.goal || "";
  const avgHr = stats.avg_hr;
  const weight = parseFloat(profile.weight)||0;
  const height = parseFloat(profile.height)||0;
  const bmi = weight&&height ? weight/Math.pow(height/100,2) : null;

  const TIPS = [
    // Water
    { id:"water1", cat:"💧 Hydration", color:"#6366f1", bg:"#e0e7ff",
      title:"Drink water first thing in the morning",
      desc:"After 7–8 hours of sleep your body is dehydrated. Drinking 1–2 glasses of water immediately after waking up kick-starts your metabolism, flushes out toxins, and improves brain function.",
      action:"Drink 250 ml right now", time:"30 sec", difficulty:"Easy",
      personalised: true, relevance:"Universal — always beneficial" },
    { id:"water2", cat:"💧 Hydration", color:"#6366f1", bg:"#e0e7ff",
      title:"Track your daily water intake",
      desc:"Most adults need 2–3 litres of water per day. Dehydration causes fatigue, headaches, and reduced cognitive performance. Use a marked bottle or app to track intake throughout the day.",
      action:"Set hourly water reminders on your phone", time:"2 min", difficulty:"Easy",
      relevance:"Especially important if you exercise regularly" },
    { id:"water3", cat:"💧 Hydration", color:"#6366f1", bg:"#e0e7ff",
      title:"Eat water-rich foods",
      desc:"Cucumbers, watermelon, oranges, and celery are 90%+ water. Including them in meals supplements your hydration and adds fibre, vitamins, and minerals.",
      action:"Add cucumber or watermelon to your next meal", time:"0 min extra", difficulty:"Easy",
      relevance:"Great for people who forget to drink" },

    // Movement
    { id:"move1", cat:"🏃 Movement", color:"#8b5cf6", bg:"#ede9fe",
      title:"5-minute morning stretch routine",
      desc:"Gentle stretching after waking up improves blood circulation, reduces morning stiffness, and signals your body to wake up. Focus on neck rolls, shoulder stretches, and forward bends.",
      action:"Do 3 stretches right now — neck, shoulders, hamstrings", time:"5 min", difficulty:"Easy",
      relevance: avgHr && avgHr > 80 ? "⭐ Recommended — your avg HR suggests stress or low activity" : "Great for everyone" },
    { id:"move2", cat:"🏃 Movement", color:"#8b5cf6", bg:"#ede9fe",
      title:"Take a 10-minute walk after meals",
      desc:"Post-meal walks reduce blood sugar spikes by up to 30%, improve digestion, and add up to 30+ minutes of light activity per day. You don't need gym clothes — just step outside.",
      action:"Walk around the block after your next meal", time:"10 min", difficulty:"Easy",
      relevance:"Excellent for metabolic health and energy" },
    { id:"move3", cat:"🏃 Movement", color:"#8b5cf6", bg:"#ede9fe",
      title:"Strength train 2–3× per week",
      desc:"Resistance training builds muscle, increases metabolism, improves bone density, and reduces injury risk. You don't need a gym — bodyweight exercises (push-ups, squats, lunges) are highly effective.",
      action:"Do 10 squats and 5 push-ups right now", time:"20–40 min", difficulty:"Medium",
      relevance: goal==="gain"?"⭐ Your goal is muscle building — this is essential":goal==="lose"?"⭐ Key for sustainable weight loss":"Important for long-term health" },
    { id:"move4", cat:"🏃 Movement", color:"#8b5cf6", bg:"#ede9fe",
      title:"Use the 2-minute rule for activity",
      desc:"If something takes less than 2 minutes — do it standing or walking. Take the stairs. Walk during phone calls. These micro-movements add up to significant daily activity.",
      action:"Take the stairs next time instead of the lift", time:"Ongoing", difficulty:"Easy",
      relevance:"Perfect for desk workers and busy schedules" },

    // Sleep
    { id:"sleep1", cat:"😴 Sleep", color:"#a78bfa", bg:"#f5f3ff",
      title:"Keep a consistent sleep schedule",
      desc:"Going to bed and waking up at the same time every day — even weekends — regulates your circadian rhythm. This leads to better sleep quality, easier waking, and improved mood.",
      action:"Set a fixed bedtime alarm for tonight", time:"1 min", difficulty:"Medium",
      relevance:"The single most impactful sleep improvement" },
    { id:"sleep2", cat:"😴 Sleep", color:"#a78bfa", bg:"#f5f3ff",
      title:"No screens 1 hour before bed",
      desc:"Blue light from phones and laptops suppresses melatonin production by up to 50%. Replace screen time with reading, stretching, or journaling. Use night mode if you must use devices.",
      action:"Enable night mode on all devices now", time:"2 min", difficulty:"Medium",
      relevance:"Reduces time to fall asleep by 15–30 min" },
    { id:"sleep3", cat:"😴 Sleep", color:"#a78bfa", bg:"#f5f3ff",
      title:"Keep your bedroom cool and dark",
      desc:"The optimal sleep temperature is 16–19°C. Darkness triggers melatonin release. Blackout curtains and a slightly open window can dramatically improve sleep depth and REM cycles.",
      action:"Open a window tonight and cover any LED lights", time:"5 min", difficulty:"Easy",
      relevance:"Improves deep sleep and morning energy" },

    // Nutrition
    { id:"nutrition1", cat:"🥗 Nutrition", color:"#34d399", bg:"#d1fae5",
      title:"Add protein to every meal",
      desc:"Protein keeps you full longer, preserves muscle mass, and requires more energy to digest. Aim for 1.2–2g per kg of body weight daily. Good sources: eggs, chicken, Greek yogurt, lentils, tofu.",
      action: weight>0 ? `Aim for ${Math.round(weight*1.5)}–${Math.round(weight*2)}g protein today` : "Add an egg or a handful of nuts to your next meal",
      time:"0 min extra", difficulty:"Easy",
      relevance: goal==="gain"?"⭐ Critical for muscle building":goal==="lose"?"⭐ Key for preserving muscle while losing fat":"Foundational for health" },
    { id:"nutrition2", cat:"🥗 Nutrition", color:"#34d399", bg:"#d1fae5",
      title:"Eat the rainbow — 5 colours per day",
      desc:"Different colours in vegetables and fruits represent different phytonutrients. Red (lycopene), orange (beta-carotene), green (chlorophyll), blue (anthocyanins), white (allicin). Together they reduce inflammation and oxidative stress.",
      action:"Count how many colours are on your plate right now", time:"0 min extra", difficulty:"Easy",
      relevance:"Reduces chronic disease risk significantly" },
    { id:"nutrition3", cat:"🥗 Nutrition", color:"#34d399", bg:"#d1fae5",
      title:"Limit processed food to 20% of meals",
      desc:"Ultra-processed foods are engineered to override your satiety signals. They spike blood sugar, cause energy crashes, and promote overeating. Cook simple whole foods — it doesn't have to be complicated.",
      action:"Replace one processed snack today with fruit or nuts", time:"0 min extra", difficulty:"Medium",
      relevance: bmi&&bmi>25?"⭐ Especially relevant for your current BMI":"Important for everyone" },

    // Mental health
    { id:"mental1", cat:"🧠 Mental Health", color:"#ec4899", bg:"#fdf2f8",
      title:"Practice 5 minutes of deep breathing",
      desc:"Box breathing (4 seconds in, 4 hold, 4 out, 4 hold) activates the parasympathetic nervous system, reducing cortisol and heart rate within minutes. Studies show it lowers anxiety as effectively as some medications.",
      action:"Do one box breathing cycle right now: 4-4-4-4", time:"5 min", difficulty:"Easy",
      relevance: avgHr&&avgHr>80?"⭐ Your elevated HR suggests this could help":"Excellent stress management tool" },
    { id:"mental2", cat:"🧠 Mental Health", color:"#ec4899", bg:"#fdf2f8",
      title:"Write 3 things you're grateful for",
      desc:"Gratitude journaling rewires the brain's negativity bias over time. Studies show just 5 minutes of daily gratitude practice improves mood, reduces anxiety, and improves sleep quality within 4 weeks.",
      action:"Write 3 things right now — they can be tiny", time:"5 min", difficulty:"Easy",
      relevance:"Proven to improve wellbeing within 4 weeks" },
    { id:"mental3", cat:"🧠 Mental Health", color:"#ec4899", bg:"#fdf2f8",
      title:"Spend 20 minutes outdoors daily",
      desc:"Natural light regulates circadian rhythms and vitamin D synthesis. Green spaces reduce cortisol levels measurably. Even cloudy outdoor light is 10–100× brighter than indoor lighting, significantly affecting mood and sleep.",
      action:"Step outside for 10 minutes after reading this", time:"20 min", difficulty:"Easy",
      relevance:"Improves mood, sleep, and vitamin D levels" },
  ];

  const cats = [...new Set(TIPS.map(t=>t.cat))];
  const [activeCat, setActiveCat] = useState("all");
  const filtered = activeCat==="all" ? TIPS : TIPS.filter(t=>t.cat===activeCat);
  const doneCount = Object.values(done).filter(Boolean).length;

  return (
    <div className="page">
      <div className="page-hdr">
        <div>
          <div className="page-title">Health Tips</div>
          <div className="page-sub">
            {doneCount > 0 ? `${doneCount} of ${TIPS.length} tips completed · keep going!` : "Personalised tips based on your data"}
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:10,marginTop:4}}>
          <div style={{fontSize:13,color:"var(--ink3)"}}>Progress</div>
          <div style={{width:120,height:8,background:"rgba(139,92,246,.15)",borderRadius:4,overflow:"hidden"}}>
            <div style={{height:"100%",width:`${Math.round(doneCount/TIPS.length*100)}%`,background:"linear-gradient(90deg,var(--blue),var(--violet))",borderRadius:4,transition:"width .4s"}}/>
          </div>
          <div style={{fontSize:13,fontWeight:700,color:"var(--violet)"}}>{Math.round(doneCount/TIPS.length*100)}%</div>
        </div>
      </div>

      {/* Category filter */}
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:24}}>
        {["all",...cats].map(c=>(
          <button key={c} onClick={()=>setActiveCat(c)} style={{
            padding:"8px 16px", borderRadius:980, border:"1.5px solid",
            borderColor: activeCat===c?"transparent":"var(--border)",
            background: activeCat===c?"linear-gradient(135deg,var(--blue),var(--violet))":"rgba(255,255,255,.7)",
            color: activeCat===c?"white":"var(--ink2)",
            fontSize:13, fontWeight:600, cursor:"pointer", transition:"all .2s",
            boxShadow: activeCat===c?"0 4px 16px rgba(139,92,246,.3)":"none",
          }}>
            {c==="all"?"✦ All tips":c}
          </button>
        ))}
      </div>

      {/* Tips grid */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))",gap:14}}>
        {filtered.map(tip=>(
          <div key={tip.id} style={{
            background: done[tip.id] ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.82)",
            backdropFilter:"blur(30px)",
            border:`1.5px solid ${done[tip.id]?"rgba(52,211,153,.3)":tip.color+"22"}`,
            borderRadius:24, padding:24,
            boxShadow: done[tip.id]?"none":"0 2px 20px rgba(99,102,241,.1)",
            transition:"all .25s", opacity: done[tip.id]?.75:1,
            borderTop:`3px solid ${done[tip.id]?"#34d399":tip.color}`,
          }}>
            {/* Header */}
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}>
              <div>
                <div style={{fontSize:10,fontWeight:700,color:tip.color,textTransform:"uppercase",letterSpacing:".08em",marginBottom:6}}>{tip.cat}</div>
                <div style={{fontSize:15,fontWeight:700,letterSpacing:"-.2px",color:done[tip.id]?"var(--ink3)":"var(--ink)",textDecoration:done[tip.id]?"line-through":"none"}}>{tip.title}</div>
              </div>
              <button onClick={()=>toggle(tip.id)} style={{
                width:28,height:28,borderRadius:"50%",border:"none",flexShrink:0,marginLeft:12,
                background: done[tip.id]?"#34d399":"rgba(139,92,246,.1)",
                color: done[tip.id]?"white":tip.color,
                fontSize:14, cursor:"pointer", transition:"all .2s", marginTop:2,
                display:"flex",alignItems:"center",justifyContent:"center",
              }}>
                {done[tip.id]?"✓":"○"}
              </button>
            </div>

            {/* Relevance badge */}
            {tip.relevance.startsWith("⭐")&&(
              <div style={{fontSize:11,fontWeight:600,padding:"4px 10px",borderRadius:20,background:tip.bg,color:tip.color,display:"inline-flex",alignItems:"center",gap:4,marginBottom:10}}>
                {tip.relevance}
              </div>
            )}

            {/* Description */}
            <div style={{fontSize:13,color:"var(--ink2)",lineHeight:1.65,marginBottom:14}}>{tip.desc}</div>

            {/* Action + meta */}
            <div style={{background:tip.bg,borderRadius:14,padding:"12px 14px",marginBottom:0}}>
              <div style={{fontSize:11,fontWeight:700,color:tip.color,textTransform:"uppercase",letterSpacing:".06em",marginBottom:4}}>Action</div>
              <div style={{fontSize:13,fontWeight:600,color:"var(--ink)"}}>→ {tip.action}</div>
              <div style={{display:"flex",gap:16,marginTop:8}}>
                <span style={{fontSize:11,color:tip.color}}>⏱ {tip.time}</span>
                <span style={{fontSize:11,color:tip.color}}>
                  {tip.difficulty==="Easy"?"🟢":"tip.difficulty"==="Medium"?"🟡":"🔴"} {tip.difficulty}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
const NAV=[{id:"upload",icon:"⬆",l:"Import data"},{id:"dashboard",icon:"◈",l:"Dashboard"},{id:"profile",icon:"◉",l:"My Profile"},{id:"tips",icon:"✦",l:"Health Tips"}];

export default function App() {
  const [user,setUser]=useState(getUser); const [page,setPage]=useState("upload");
  const [uploadData,setUploadData]=useState(null); const [showAcc,setShowAcc]=useState(false);
  const onAuth=useCallback(data=>{setUser({user_id:data.user_id,email:data.email,name:data.name});},[]);
  const logout=()=>{clearAuth();setUser(null);setUploadData(null);setPage("upload");};
  const onUploaded=useCallback(data=>{setUploadData(data);setPage("dashboard");},[]);
  const onUpdated=useCallback(u=>{setUser(u);setShowAcc(false);},[]);
  if(!user) return <AuthPage onAuth={onAuth}/>;
  return (
    <>
      <style>{css}</style>
      <div className="shell">
        <aside className="sidebar">
          <div className="logo"><div className="logo-dot">♥</div><div className="logo-text">HealthPlatform</div></div>
          <div className="nav-lbl">Navigation</div>
          {NAV.map(n=>(
            <button key={n.id} className={`nav-btn${page===n.id?" active":""}`} onClick={()=>setPage(n.id)}>
              <div className="nav-icon">{n.icon}</div>{n.l}
            </button>
          ))}

          <div className="sidebar-foot">
            <div className="user-row" onClick={()=>setShowAcc(true)} title="Account settings">
              <div className="user-av">{(user.name||"U")[0].toUpperCase()}</div>
              <div><div className="user-name">{user.name}</div><div className="user-email">{user.email}</div></div>
              <div className={`live-badge ${uploadData?"live-on":"live-off"}`}>{uploadData?"Live":"Offline"}</div>
            </div>
          </div>
        </aside>
        <main className="main">
          {page==="upload"    && <UploadPage    onUploaded={onUploaded}/>}
          {page==="dashboard" && <DashboardPage uploadData={uploadData}/>}
          {page==="profile"   && <ProfilePage/>}
          {page==="tips"      && <TipsPage uploadData={uploadData}/>}
        </main>
      </div>
      <ChatWidget uploadData={uploadData}/>
      {showAcc&&<AccountModal user={user} onClose={()=>setShowAcc(false)} onUpdated={onUpdated} onLogout={logout}/>}
    </>
  );
}