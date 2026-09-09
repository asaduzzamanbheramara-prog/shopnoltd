import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  resolve: {
    alias: [
      {
        find: /^android-emulator-webrtc$/,
        replacement: fileURLToPath(
          new URL("./node_modules/android-emulator-webrtc/dist/index.js", import.meta.url),
        ),
      },
    ],
  },
});
