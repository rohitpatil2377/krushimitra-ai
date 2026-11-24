import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

// Initialize translations once, as early as possible.
import '@/i18n';
import { loadSavedApiUrl } from '@/config';
import { Colors } from '@/constants/colors';
import { useAuth } from '@/store/useAuth';

export default function RootLayout() {
  // Gate the first render on two storage reads: the backend URL and the saved session.
  // Screens fetch on mount, so rendering first would fire those requests at the wrong host and
  // without the farmer's token, then show sample data for a second before correcting itself.
  const [ready, setReady] = useState(false);
  const hydrateAuth = useAuth((s) => s.hydrate);

  useEffect(() => {
    void (async () => {
      await loadSavedApiUrl();
      await hydrateAuth();
      setReady(true);
    })();
  }, [hydrateAuth]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar style="light" />
        {ready ? (
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="login" options={{ presentation: 'modal' }} />
            <Stack.Screen name="cycle/[id]" />
            <Stack.Screen name="cycle/new" options={{ presentation: 'modal' }} />
          </Stack>
        ) : (
          <View style={{ flex: 1, backgroundColor: Colors.bg }} />
        )}
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
