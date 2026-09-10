import fs from 'node:fs';
import path from 'node:path';

const here = import.meta.dirname;
const cuts = [0, 180, 410, 590, 770, 920];
const colors = ['#c8d7d1','#a7c6b9','#c8d7d1','#a7c6b9','#c8d7d1'];
const S = 1.25, ox = 45, oy = 330;
const x = n => ox + n * S, z = n => oy - n * S;
const modules = cuts.slice(0,-1).map((a,i) => {
  const b=cuts[i+1]; return `<rect x="${x(a)}" y="${z(238)}" width="${(b-a)*S}" height="${238*S}" fill="${colors[i]}" stroke="#315449" stroke-width="2"/><text x="${x((a+b)/2)}" y="${z(112)}" text-anchor="middle" font-size="15">模块 ${i+1}<tspan x="${x((a+b)/2)}" dy="18">${b-a} mm</tspan></text>`;
}).join('');
const seams = cuts.slice(1,-1).map(s => `<line x1="${x(s)}" y1="${z(238)}" x2="${x(s)}" y2="${z(0)}" stroke="#c94840" stroke-width="3"/>${[52,168].map(y=>`<path d="M ${x(s-5)} ${z(7)} L ${x(s+5)} ${z(7)} L ${x(s)} ${z(1)} Z" fill="#d99a36"/>`).join('')}${[66,180].map(h=>`<path d="M ${x(s-5)} ${z(h)} L ${x(s+5)} ${z(h)} L ${x(s)} ${z(h+5)} Z" fill="#d99a36"/>`).join('')}`).join('');
const decks=[66,129,192].map(h=>`<rect x="${x(0)}" y="${z(h+5)}" width="${180*S}" height="${5*S}" fill="#657a8a"/><rect x="${x(180)}" y="${z(h+5)}" width="${180*S}" height="${5*S}" fill="#657a8a"/><path d="M ${x(180)} ${z(h+5)} l ${-7} ${6} l ${14} 0 Z" fill="#d99a36"/>`).join('');
const billboard=`<rect x="${x(0)}" y="${z(394)}" width="${360*S}" height="${64*S}" fill="#16181c"/><line x1="${x(90)}" y1="${z(238)}" x2="${x(90)}" y2="${z(330)}" stroke="#16181c" stroke-width="10"/><line x1="${x(270)}" y1="${z(238)}" x2="${x(270)}" y2="${z(330)}" stroke="#16181c" stroke-width="10"/><text x="${x(180)}" y="${z(373)}" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="bold" fill="white">Lovely Cars</text><text x="${x(180)}" y="${z(345)}" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="bold" fill="white">I've Driven</text>`;
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1250" height="560" viewBox="0 0 1250 560"><rect width="100%" height="100%" fill="white"/><text x="45" y="32" font-family="sans-serif" font-size="22" font-weight="bold">v2 装配正视预览：五个一体模块、三层榫接层板与广告牌</text>${modules}${seams}<rect x="${x(0)}" y="${z(8)}" width="${920*S}" height="${8*S}" fill="#4e5965"/>${decks}${billboard}<line x1="${x(10)}" y1="${z(8)}" x2="${x(10)}" y2="${z(230)}" stroke="#d6a115" stroke-width="5"/><line x1="${x(340)}" y1="${z(8)}" x2="${x(340)}" y2="${z(230)}" stroke="#d6a115" stroke-width="5"/><rect x="${x(360)}" y="${z(238)}" width="${6*S}" height="${230*S}" fill="#45525e"/><rect x="${x(914)}" y="${z(238)}" width="${6*S}" height="${230*S}" fill="#45525e"/><text x="45" y="535" font-family="sans-serif" font-size="14">灰：主体模块；黄：车库承托柱；橙：每层两组榫接；广告牌支架中心 X=90、270 mm，对称于 X=180 mm。</text></svg>`;
fs.writeFileSync(path.join(here,'assembly-preview.svg'),svg);

const parts = cuts.slice(0,-1).map((a,i)=>{const b=cuts[i+1], w=b-a+(i<4?14:0);return `<rect x="${x(a)}" y="${z(220)}" width="${w*S}" height="${220*S}" fill="${colors[i]}" stroke="#315449" stroke-width="2"/><text x="${x(a+w/2)}" y="${z(105)}" text-anchor="middle" font-size="14">模块 ${i+1}<tspan x="${x(a+w/2)}" dy="17">${w} × 220 × 238</tspan></text>`}).join('');
fs.writeFileSync(path.join(here,'parts-preview.svg'),`<svg xmlns="http://www.w3.org/2000/svg" width="1250" height="350" viewBox="0 0 1250 350"><rect width="100%" height="100%" fill="white"/><text x="45" y="30" font-family="sans-serif" font-size="22" font-weight="bold">v2 主体分件图（含公榫实际突出包络）</text>${parts}</svg>`);
