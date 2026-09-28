import { useEffect, useState } from 'react'

const STORAGE_API = import.meta.env.VITE_STORAGE_API_URL || 'https://storage-service.shopnoltd.dpdns.org'
const API_PATH = '/api/v1/profile-videos'

function mediaUrl(url) {
  if (!url) return ''
  return url.startsWith('http') ? url : `${STORAGE_API}${url}`
}

function Embed({ video }) {
  if (video.source_type === 'upload') {
    return <video className="pvg-video" controls preload="metadata" playsInline src={mediaUrl(video.stream_url)} />
  }
  if (video.source_type === 'direct') {
    return <video className="pvg-video" controls preload="metadata" playsInline src={video.embed_ref} />
  }
  const src = video.embed_provider === 'youtube'
    ? `https://www.youtube.com/embed/${encodeURIComponent(video.embed_ref)}`
    : `https://player.vimeo.com/video/${encodeURIComponent(video.embed_ref)}`
  return <iframe className="pvg-video" src={src} title={video.title} loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen />
}

export default function ProfileVideoGallery({ profileSlug, variant = 'gallery', className = '' }) {
  const [videos, setVideos] = useState([])

  useEffect(() => {
    let active = true
    fetch(`${STORAGE_API}${API_PATH}/public/${encodeURIComponent(profileSlug)}`, { headers: { Accept: 'application/json' } })
      .then(response => response.ok ? response.json() : [])
      .then(data => { if (active) setVideos(Array.isArray(data) ? data : []) })
      .catch(() => { if (active) setVideos([]) })
    return () => { active = false }
  }, [profileSlug])

  if (!videos.length) return null

  return (
    <section className={`pvg ${variant === 'hero' ? 'pvg-hero' : ''} ${className}`} aria-label="Profile videos">
      <style>{`.pvg { width: 100%; box-sizing: border-box; } .pvg-heading { margin-bottom: 20px; } .pvg-kicker { font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: .08em; margin: 0 0 6px; opacity: .72; } .pvg-heading h2 { font-family: 'Source Serif 4', Georgia, serif; font-size: 28px; margin: 0; } .pvg-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 22px; } .pvg-card { overflow: hidden; border-radius: 7px; background: rgba(255,255,255,.96); color: #18202a; border: 1px solid rgba(0,0,0,.1); } .pvg-video { display: block; width: 100%; aspect-ratio: 16/9; border: 0; background: #0e1319; object-fit: contain; } .pvg-copy { padding: 14px 16px 17px; } .pvg-copy h3 { margin: 0 0 6px; font-size: 17px; } .pvg-copy p { margin: 0; line-height: 1.55; font-size: 14px; color: #5b6472; } .pvg-hero .pvg-grid { display: block; } .pvg-hero .pvg-card { background: rgba(26,19,16,.95); color: #efe8db; border-color: rgba(239,232,219,.15); } .pvg-hero .pvg-copy { padding: 12px 14px 14px; } .pvg-hero .pvg-copy p { color: rgba(239,232,219,.75); } @media (max-width: 640px) { .pvg-grid { grid-template-columns: 1fr; } }`}</style>
      {variant !== 'hero' && <div className="pvg-heading"><p className="pvg-kicker">VIDEO GALLERY</p><h2>Selected work &amp; walkthroughs</h2></div>}
      <div className="pvg-grid">
        {videos.map(video => (
          <article className="pvg-card" key={video.id}>
            <Embed video={video} />
            <div className="pvg-copy">
              <h3>{video.title}</h3>
              {video.description && <p>{video.description}</p>}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
