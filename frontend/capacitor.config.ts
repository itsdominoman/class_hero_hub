import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.classherohub.app',
  appName: 'Class Hero Hub',
  webDir: 'build',
  server: {
    androidScheme: 'https'
  }
};

export default config;
