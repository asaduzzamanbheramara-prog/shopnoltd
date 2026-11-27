# Professional Profiles, Video Sharing, and Universal Recovery — Delivery Specification

## Scope

This specification defines two connected Shopnoltd capabilities: every registered user can build and publish a professional profile with profile-specific videos; and visitors can use guided online recovery/software installation plus offline recovery media for supported devices and operating systems.

This is an implementation specification, not a claim that the features are already complete or deployed.

## A. Professional profile for every user

### User experience
- Every account receives a stable profile URL based on a unique, reserved slug.
- The owner can edit professional headline, summary, skills, services, work history, education, portfolio links, contact preferences, downloadable CV/portfolio, and profile photo.
- The owner can upload MP4/WebM videos or add approved YouTube/Vimeo/direct-video embeds, with title, description, thumbnail, ordering, and publish/draft state.
- A profile page is responsive and readable on phones, tablets, laptops, and desktops.
- The owner controls visibility: private/draft, unlisted link, or public/indexable. Newly created profiles must not expose private personal data by default.
- Profile owners can share a stable URL and QR code. A profile update appears at the same URL after publication.
- Profile owners can remove, reorder, unpublish, or replace their own videos. Platform admins can moderate abusive, infringing, unsafe, or policy-violating content with an audit trail.

### Link preview behaviour
- Public/unlisted share pages must provide server-rendered or edge-rendered metadata before page JavaScript runs: canonical URL, title, description, Open Graph title/description/image, Twitter card metadata, and a stable video thumbnail.
- Add video metadata only where supported by the receiving platform; never promise autoplay or inline video playback in every messaging/social application. The receiver controls preview rendering and playback.
- Provide a preview image generated from an owner-provided thumbnail or an approved video frame. Do not expose private video URLs or hidden profile fields in metadata.
- Include crawler tests for major social/messaging unfurl clients and generic preview fetchers where practical.
- A human opening the link sees the complete published profile and embedded playable videos, subject to the profile visibility setting.
- Private/draft profiles must not be available to anonymous crawlers; use authorization and noindex/no-store metadata as appropriate.

### Backend and data model
- Replace the hard-coded two-slug video allowlist with ownership-aware profile records.
- Introduce/confirm a canonical ProfessionalProfile entity with: id, owner subject/user ID, unique slug, visibility, display name, headline, summary, structured profile content, avatar/cover references, canonical URL, publication timestamps, and audit timestamps.
- Associate ProfileVideo and ProfileVideoUpload with profile ID and owner subject. Keep profile slug only as a stable routing/cache field if needed.
- Enforce owner authorization for create/update/delete/reorder/upload/publish operations; platform admins get a separately audited moderation path. Never treat possession of a slug as write authorization.
- Public video listing returns only published videos belonging to a public or valid unlisted profile. Draft/private videos require owner authorization.
- Preserve existing data-management and interior-business profiles and their published content during migration. No destructive data migration; provide a reversible migration and backup/rollback plan.
- Validate file size/type and inspect actual media content; use malware scanning/transcoding/thumbnail generation in a controlled worker. Do not trust browser MIME type or arbitrary remote embed URLs.
- Add rate limits, quotas, storage lifecycle controls, abuse reporting, and upload cleanup for abandoned chunks.

### Frontend
- Add a reusable ProfessionalProfile page driven by profile API data rather than a two-profile hard-coded switch.
- Add a protected owner editor and video manager available to all eligible users.
- Keep the existing two office profile URLs and preserve their current content, PDFs, portfolio links, QR/share behaviour, and video galleries.
- Add preview/share controls and a profile visibility indicator.
- Use safe defaults for phone/email/address: owner explicitly chooses which contact fields are public.

### Acceptance tests
- New user can create, edit, preview, publish, unpublish, and share a professional profile.
- User A cannot edit, upload to, unpublish, or delete User B's profile/videos by changing a URL or request body.
- Platform admin moderation is auditable and does not silently impersonate the owner.
- Public profile and published videos are visible without login; draft/private content is not.
- Open Graph metadata is present in the initial HTML response and points to an accessible, stable preview image.
- Existing two office profile URLs continue to work and retain their current content.
- Profile and video layout works at mobile, tablet, and desktop viewports.

## B. Universal online and offline recovery / software installation

### Online mode
- Identify target device by manufacturer/model, hardware revision where relevant, OS/version, CPU architecture, and recovery goal.
- Show only official vendor or reviewed publisher sources, compatibility, version, licence, file size, release date, and verification instructions.
- Provide guided troubleshooting, backup, repair, driver, OS installation, and application installation steps.
- Distinguish read-only diagnosis, non-destructive repair, and data-erasing reset/reinstall.
- Provide a software catalogue across supported OS families (Windows, macOS, Linux distributions, Android, iOS/iPadOS, ChromeOS and other catalogued platforms), but only list packages/install methods supported by the publisher and target platform.
- Never run arbitrary installer commands from user-generated catalogue data. A future local helper must map reviewed product IDs to fixed, signed installer sources and allow-listed arguments.

### Offline / pendrive mode
- Offer downloadable, versioned recovery plans and offline documentation that can be saved to a USB.
- For supported PCs, guide users to create bootable USB media from official OS/recovery images and verify publisher signatures/checksums before writing.
- Clearly identify when a USB is a bootable PC installer, a file-storage device, an OEM recovery medium, or a cable-connected phone restore method; these are not interchangeable.
- A future USB writer must be a separately installed, signed local helper with least privilege, explicit physical-drive selection, model/capacity display, system-disk exclusion, a second destructive confirmation, cancellation/flush, write verification, and secret-free audit logs.
- Existing user USB drives must never be formatted or overwritten by default. A selected drive is considered destructive until the user confirms the exact device and contents can be erased.
- Keep large proprietary OS images and commercial installers at their official publisher sources unless redistribution is expressly licensed.

### Device-family limitations
- Windows PCs and compatible Linux PCs can commonly boot supported installation/recovery USB media.
- Apple Mac recovery is model/architecture-specific; Apple Silicon and Intel workflows differ.
- Android phones use manufacturer-specific OTA/recovery/service methods; a generic PC bootable USB does not boot an Android phone.
- iPhone/iPad restores generally use Apple-supported computer/recovery workflows, not generic bootable USB media.
- ChromeOS uses model-specific Chromebook recovery media and verified recovery workflows.
- Other devices (TVs, routers, consoles, wearables, embedded boards) need their own model-specific, vendor-supported procedures.
- Never label a device or OS fully supported until official sources, compatibility, tests, and recovery outcomes are verified.

### Recovery tutorial videos
- Each recovery catalogue entry should have a tutorial section with: target device/model, exact OS/build, prerequisites, backup warning, tools/media, step-by-step chapters, expected screen states, failure/rollback guidance, and whether the method erases data.
- Separate online repair, offline USB recovery, and vendor-specific phone/tablet recovery tutorials.
- Videos must be paired with written steps, captions/transcripts, source links, version/date, and safety notices. Do not rely on video alone for destructive steps.
- Do not publish a video as a successful recovery demonstration unless it was actually tested on the stated model/build or clearly labelled as a simulation/walkthrough.
- Shopnoltd can host owner-approved videos or embed licensed videos; video assets must be supplied/approved and hosted through the reviewed storage pipeline.

### Security and release gates
- Read-only inventory and planning first.
- Verify backups and recovery keys before any destructive operation.
- No remote wipe, formatting, firmware flashing, bootloader unlocking, or software installation without explicit, target-specific user confirmation.
- Require signed releases, trusted checksums, source/licence review, malware scanning, and staged tests.
- Test images in disposable VMs and on physical reference devices before claiming hardware support; VM-only tests do not establish physical-device compatibility.
- Keep recovery credentials, signing keys, API tokens, and user backups out of public Git.
- Production deployment occurs only through the existing reviewed CI/GitOps path after tests pass.

## C. Delivery sequence

1. Inventory current profile/auth/storage APIs, DB migrations, frontend routes, and existing two office profile content.
2. Implement the canonical profile model, ownership authorization, reversible migration, and tests.
3. Implement reusable public profile rendering and owner editor/video management for all users.
4. Implement server/edge-rendered social metadata and crawler/unfurl tests.
5. Add owner-controlled visibility, contact privacy, moderation, quota, and abuse controls.
6. Expand the recovery catalogue and attach reviewed written/video tutorials per device/OS.
7. Implement offline downloadable guides and signed recovery-media manifests.
8. Build a separate local USB writer only after a security review and destructive-action test plan.
9. Validate on staging, preserve existing services/data, then deploy via GitOps.

## Current-state notes (verified from repository inspection)
- The storage service currently restricts profile videos to the hard-coded slugs data-management and interior-business.
- The current admin video page exposes only those two profiles.
- The current public profile page has static profile objects and does not load the shared video gallery.
- The existing two dedicated office pages already include a ProfileVideoGallery.
- The current recovery catalogue and planner are metadata/documentation tools; they do not write a USB or prove a physical device has been repaired.
- The inspected HP Laptop 14s-cf2xxx and realme C35 RMX3511 records are model-specific guidance, not tested restore evidence.