import { AdsterraBannerZone } from './AdsterraAds'

// Keep the existing homepage placement and zone identity stable.
export default function AdsterraBanner() {
  return <AdsterraBannerZone name="300x250" maxWidth={340} />
}
