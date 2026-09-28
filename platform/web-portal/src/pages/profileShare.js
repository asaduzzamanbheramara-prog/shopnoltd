// Shared by DataManagementProfile.jsx and InteriorBusinessProfile.jsx.
// Keeps the QR code and share behaviour that PublicProfiles.jsx already offered.

export function qrUrl(url) {
  return 'https://api.qrserver.com/v1/create-qr-code/?size=320x320&margin=12&data=' + encodeURIComponent(url)
}

export async function shareProfile(url, title) {
  const shareData = { title, text: 'View this Shopnoltd profile', url }
  try {
    if (navigator.share) {
      await navigator.share(shareData)
      return
    }
  } catch (err) {
    // The person closed the share sheet on purpose; do nothing.
    if (err && err.name === 'AbortError') return
  }
  try {
    await navigator.clipboard.writeText(url)
    window.alert('Profile link copied to clipboard')
  } catch {
    window.prompt('Copy this profile link:', url)
  }
}
