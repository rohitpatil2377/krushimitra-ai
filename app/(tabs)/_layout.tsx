import { Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Text } from 'react-native';

import { Colors } from '@/constants/colors';

/** Renders an emoji as a tab-bar icon (no icon library needed = lighter app). */
function TabEmoji({ emoji, focused }: { emoji: string; focused: boolean }) {
  return <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.55 }}>{emoji}</Text>;
}

export default function TabsLayout() {
  const { t } = useTranslation();

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: Colors.primary },
        headerTintColor: Colors.white,
        headerTitleStyle: { fontSize: 20, fontWeight: '700' },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarStyle: { height: 62, paddingBottom: 8, paddingTop: 6 },
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: t('appName'),
          tabBarLabel: t('tabs.home'),
          tabBarIcon: ({ focused }) => <TabEmoji emoji="🏠" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="diagnose"
        options={{
          title: t('features.diagnose.title'),
          tabBarLabel: t('tabs.diagnose'),
          tabBarIcon: ({ focused }) => <TabEmoji emoji="🌿" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: t('features.chat.title'),
          tabBarLabel: t('tabs.chat'),
          tabBarIcon: ({ focused }) => <TabEmoji emoji="💬" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="weather"
        options={{
          title: t('features.weather.title'),
          tabBarLabel: t('tabs.weather'),
          tabBarIcon: ({ focused }) => <TabEmoji emoji="☁️" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="irrigation"
        options={{
          title: t('features.irrigation.title'),
          tabBarLabel: t('tabs.irrigation'),
          tabBarIcon: ({ focused }) => <TabEmoji emoji="💧" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="market"
        options={{
          title: t('features.market.title'),
          tabBarLabel: t('tabs.market'),
          tabBarIcon: ({ focused }) => <TabEmoji emoji="📈" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
