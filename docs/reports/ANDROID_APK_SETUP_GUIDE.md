# 📱 Android KoBoCollect APK - Setup Guide

**Status:** ✅ Backend Ready | ⚠️ APK Installation Required

---

## What You Need to Know

Your **KoBoCAT API is fully operational** and ready to serve mobile apps. However, to use forms on Android devices, you need to install the **KoBoCollect APK** (Android application).

---

## ❌ What's NOT Working Yet

- ❌ Android app is NOT built into the server (by design)
- ❌ You cannot access via browser at `https://kf.shopnoltd.dpdns.org` with mobile app features

## ✅ What IS Working

- ✅ **API endpoints** for Android apps (`https://kf.shopnoltd.dpdns.org`)
- ✅ **Form sync** capability  
- ✅ **Data submission** endpoints
- ✅ **Media upload** support
- ✅ **Offline mode** support
- ✅ **GPS collection** ready

---

## 📥 How to Get KoBoCollect on Android

### Option 1: Download from Google Play Store (EASIEST)
```
1. Open Google Play Store on Android device
2. Search for: "KoBoCollect"
3. Tap "Install"
4. Wait for installation to complete
```

### Option 2: Download APK File
```
1. Go to: https://github.com/kobotoolbox/collect/releases
2. Download latest .apk file (e.g., collect-v4.x.x.apk)
3. Transfer to Android device
4. Open file manager, find the APK
5. Tap and install
```

### Option 3: Use Beta Version
```
1. Visit: https://play.google.com/apps/testing/org.kobotoolbox.collect
2. Join beta program
3. Install from Play Store (beta version)
```

---

## ⚙️ Configure KoBoCollect for Your Server

After installation:

1. **Open KoBoCollect** app
2. **Tap Menu** (three dots) → **Settings**
3. **Tap General Settings**
4. **Enter Server URL:** `https://kf.shopnoltd.dpdns.org`
5. **Enter Port:** `443` (HTTPS default)
6. **Enable SSL:** ✓ (checked)
7. **Save settings**
8. **Go back** and **Fetch Blank Form**
9. **Enter username** (your KoBoToolbox account)
10. **Enter password** (your KoBoToolbox password)
11. **Download forms** you created
12. **Start collecting data offline**

---

## 📋 KoBoCollect Features

Once installed, you can:

- ✅ Download forms from KoBoToolbox
- ✅ Fill forms offline (no internet needed)
- ✅ Collect GPS coordinates
- ✅ Take photos/videos
- ✅ Scan barcodes
- ✅ Record audio
- ✅ Add signatures
- ✅ Skip validation rules
- ✅ Sync when internet returns
- ✅ Track submission status

---

## 🔌 API Endpoints Available

Your backend API supports:

```bash
GET    /api/v2/forms              # List forms
GET    /api/v2/forms/{id}         # Get form details
GET    /api/v2/forms/{id}/form.xml # Download XForm
POST   /api/submission            # Submit data
PUT    /api/submission/{id}       # Update submission
GET    /api/submission            # List submissions
DELETE /api/submission/{id}       # Delete submission
```

---

## 🛠️ Troubleshooting

### "Cannot Connect to Server"
- ✓ Check URL: `https://kf.shopnoltd.dpdns.org`
- ✓ Check SSL is enabled
- ✓ Check internet connection
- ✓ Wait 30 seconds and try again

### "Login Failed"
- ✓ Verify username (email or username)
- ✓ Verify password is correct
- ✓ Check Caps Lock
- ✓ Try resetting password on web (https://kobo.shopnoltd.dpdns.org)

### "No Forms Available"
- ✓ Create a form in KoBoToolbox first
- ✓ Publish the form
- ✓ In app, tap "Fetch Blank Form"
- ✓ Select the form and download
- ✓ Tap "Fill Blank Form" to start

### "Cannot Submit Data"
- ✓ Check internet connection
- ✓ Verify form is complete
- ✓ Check for validation errors
- ✓ Try submitting after 30 seconds

---

## 📊 Workflow: Create Form → Collect → Submit

```
1. Create Form on Web
   └─→ https://kobo.shopnoltd.dpdns.org
       • Create project
       • Add questions
       • Publish

2. Setup Mobile
   └─→ Install KoBoCollect APK
   └─→ Configure server (https://kf.shopnoltd.dpdns.org)
   └─→ Login with credentials
   └─→ Download form

3. Collect Data Offline
   └─→ Open form
   └─→ Answer questions
   └─→ Add media (photos, GPS, etc)
   └─→ Save locally

4. Submit When Online
   └─→ Tap "Send Data"
   └─→ View submission status
   └─→ See data in web dashboard

5. Analyze Results
   └─→ Go to https://kobo.shopnoltd.dpdns.org
   └─→ View submissions table
   └─→ Export to Excel/CSV
```

---

## 🖥️ Web vs Mobile Features

| Feature | Web (Browser) | Mobile (KoBoCollect) |
|---------|---------------|---------------------|
| Create Forms | ✓ Yes | ✗ No |
| Fill Forms | ✓ Yes | ✓ Yes |
| Offline Mode | ✗ No | ✓ Yes |
| GPS Location | ✓ Limited | ✓ Full |
| Camera | ✓ Yes | ✓ Yes |
| Barcode Scan | ✗ No | ✓ Yes |
| Audio Record | ✗ No | ✓ Yes |
| Signature | ✗ No | ✓ Yes |
| Bulk Download | ✗ No | ✓ Yes |
| Background Sync | ✗ No | ✓ Yes |

---

## 📱 Supported Android Versions

- **Minimum:** Android 5.0 (API 21)
- **Tested:** Android 5.0 - 14.0
- **Recommended:** Android 8.0+

---

## 🚀 Get Started Now

1. **Install APK:** Google Play Store → Search "KoBoCollect" → Install
2. **Configure:** Server: `https://kf.shopnoltd.dpdns.org`
3. **Login:** Use your KoBoToolbox credentials
4. **Download:** Fetch forms from your projects
5. **Collect:** Start filling forms offline
6. **Submit:** Send data when connected

---

## 💡 Pro Tips

- **Create test form first:** Test the workflow before real deployment
- **Add offline instructions:** Include offline forms description
- **Use progress bars:** Let users see form completion
- **Download backup forms:** Always have copies of forms
- **Test connectivity:** Verify connection before large deployment
- **Monitor submissions:** Check dashboard regularly for responses

---

## 📞 Support

For KoBoCollect issues:
- **Android:** Google Play Store → App page → Leave review/comment
- **GitHub:** https://github.com/kobotoolbox/collect/issues
- **Documentation:** https://docs.kobotoolbox.org/mobile-form-collection/

For your server issues:
- **Check API:** `curl https://kf.shopnoltd.dpdns.org/api/v2`
- **View logs:** `kubectl logs -n toolbox deployment/kf`
- **Restart service:** `kubectl rollout restart deployment/kf -n toolbox`

---

## ✅ Verification Checklist

Before deploying to production:

- [ ] APK installed on test device
- [ ] Server configured correctly
- [ ] Login works with test account
- [ ] Forms download successfully
- [ ] Can fill form offline
- [ ] Can submit when connected
- [ ] Data appears in web dashboard
- [ ] Photos/media sync correctly
- [ ] GPS coordinates recording
- [ ] Multiple devices tested

---

## 🎯 Summary

| Item | Status | Action |
|------|--------|--------|
| **Backend API** | ✅ Ready | Nothing needed |
| **Web Forms** | ✅ Working | Use now |
| **Mobile API** | ✅ Ready | Nothing needed |
| **Android App** | ⚠️ Needed | Install from Play Store |
| **Configuration** | ℹ️ Manual | Follow setup guide |
| **Offline Collection** | ✅ Ready | Use KoBoCollect |
| **Data Sync** | ✅ Ready | Automatic when online |

---

**Your KoBoCAT backend is fully operational and ready to receive mobile form submissions!**  
**Simply install the APK and start collecting data.**

For more information, visit: https://docs.kobotoolbox.org/
