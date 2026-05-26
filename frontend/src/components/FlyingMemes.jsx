import React from 'react'

const MEMES = [
  { url: 'https://i.imgflip.com/1bij.jpg',   dur: 20, delay: 0,   bot: '5%',  size: 90,  rot: '-6deg',  dir: 'right', bob: 3.2 },
  { url: 'https://i.imgflip.com/4t0m5.jpg',  dur: 26, delay: 8,   bot: '18%', size: 75,  rot: '9deg',   dir: 'left',  bob: 2.7 },
  { url: 'https://i.imgflip.com/2wifvo.jpg', dur: 19, delay: 4,   bot: '4%',  size: 70,  rot: '4deg',   dir: 'right', bob: 3.8 },
  { url: 'https://i.imgflip.com/1e7ql7.jpg', dur: 30, delay: 15,  bot: '28%', size: 85,  rot: '-11deg', dir: 'left',  bob: 2.4 },
  { url: 'https://i.imgflip.com/23ls.jpg',   dur: 22, delay: 6,   bot: '38%', size: 68,  rot: '13deg',  dir: 'right', bob: 4.0 },
  { url: 'https://i.imgflip.com/3lhx3p.jpg', dur: 28, delay: 20,  bot: '12%', size: 80,  rot: '-4deg',  dir: 'left',  bob: 3.5 },
  { url: 'https://i.imgflip.com/2gnhut.jpg', dur: 16, delay: 2,   bot: '43%', size: 65,  rot: '7deg',   dir: 'right', bob: 2.9 },
  { url: 'https://i.imgflip.com/4acd7j.png', dur: 24, delay: 12,  bot: '22%', size: 73,  rot: '-8deg',  dir: 'left',  bob: 3.3 },
  { url: 'https://i.imgflip.com/3oevdk.jpg', dur: 32, delay: 18,  bot: '32%', size: 60,  rot: '5deg',   dir: 'right', bob: 3.7 },
  { url: 'https://i.imgflip.com/1otk96.jpg', dur: 21, delay: 9,   bot: '8%',  size: 78,  rot: '-14deg', dir: 'left',  bob: 2.5 },
]

export default function FlyingMemes() {
  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: '50vh',
      overflow: 'hidden',
      pointerEvents: 'none',
      zIndex: 2,
    }}>
      {MEMES.map((m, i) => (
        <div
          key={i}
          className="fly-meme-outer"
          style={{
            bottom: m.bot,
            width: m.size,
            height: m.size,
            opacity: 0.38,
            animation: `${m.dir === 'right' ? 'flyHorizRight' : 'flyHorizLeft'} ${m.dur}s linear -${m.delay}s infinite`,
          }}
        >
          <div
            className="fly-meme-inner"
            style={{
              '--fly-rot': m.rot,
              animation: `memeBob ${m.bob}s ease-in-out -${(m.delay * 0.4).toFixed(1)}s infinite`,
            }}
          >
            <img src={m.url} alt="" loading="lazy" />
          </div>
        </div>
      ))}
    </div>
  )
}
