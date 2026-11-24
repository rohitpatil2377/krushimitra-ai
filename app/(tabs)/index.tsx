import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import BackendSetting from '@/components/BackendSetting';
import CycleCard from '@/components/CycleCard';
import FeatureCard from '@/components/FeatureCard';
import LanguageToggle from '@/components/LanguageToggle';
import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { UnauthorizedError } from '@/services/api';
import { listCycles } from '@/services/twin';
import type { CycleSummary } from '@/services/twin';
import { useAuth } from '@/store/useAuth';

// Home is the farm dashboard, not just a launcher.
//
// The crop twin sits above the feature cards because it is the thing a farmer opens the app for
// daily — "how is my onion doing" — while diagnosis and mandi prices are occasional. A seventh
// tab would have squeezed the tab bar on a 5-inch phone for something that belongs here anyway.

const FEATURES = [
  { key: 'diagnose', emoji: '🌿', route: '/diagnose' },
  { key: 'chat', emoji: '💬', route: '/chat' },
  { key: 'weather', emoji: '☁️', route: '/weather' },
  { key: 'irrigation', emoji: '💧', route: '/irrigation' },
  { key: 'market', emoji: '📈', route: '/market' },
] as const;

export default function HomeScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { isSignedIn, signOut, farmer } = useAuth();
  const signedIn = isSignedIn();

  const [cycles, setCycles] = useState<CycleSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    if (!signedIn) {
      setCycles([]);
      return;
    }
    setLoading(true);
    setFailed(false);
    try {
      setCycles(await listCycles());
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        void signOut();
      } else {
        console.warn('[home] could not load cycles:', error);
        setFailed(true);
      }
    } finally {
      setLoading(false);
    }
  }, [signedIn, signOut]);

  // Refetch on focus: a cycle added or harvested on another screen must show up on return.
  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  return (
    <ScreenContainer>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.greeting}>{t('home.greeting')}</Text>
          <Text style={styles.tagline}>{t('tagline')}</Text>
        </View>
        <LanguageToggle />
      </View>

      {/* --- my farm --- */}
      <View style={styles.sectionHead}>
        <Text style={styles.sectionTitle}>{t('twin.myFarm')}</Text>
        {signedIn && (
          <Pressable onPress={() => router.push('/cycle/new')}>
            <Text style={styles.addLink}>+ {t('twin.addCycle')}</Text>
          </Pressable>
        )}
      </View>

      {!signedIn && (
        <Pressable style={styles.loginCard} onPress={() => router.push('/login')}>
          <Text style={styles.loginTitle}>🔐 {t('twin.loginPrompt')}</Text>
          <Text style={styles.loginBody}>{t('twin.loginWhy')}</Text>
        </Pressable>
      )}

      {signedIn && loading && cycles.length === 0 && (
        <ActivityIndicator style={styles.spinner} color={Colors.primary} />
      )}

      {signedIn && failed && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyBody}>{t('twin.loadFailed')}</Text>
          <Pressable style={styles.retryBtn} onPress={() => void load()}>
            <Text style={styles.retryText}>{t('weatherScreen.retry')}</Text>
          </Pressable>
        </View>
      )}

      {signedIn && !loading && !failed && cycles.length === 0 && (
        <Pressable style={styles.emptyCard} onPress={() => router.push('/cycle/new')}>
          <Text style={styles.emptyTitle}>🌱 {t('twin.firstCycle')}</Text>
          <Text style={styles.emptyBody}>{t('twin.firstCycleWhy')}</Text>
        </Pressable>
      )}

      {cycles.map((cycle) => (
        <CycleCard
          key={cycle.id}
          cycle={cycle}
          onPress={() => router.push(`/cycle/${cycle.id}`)}
        />
      ))}

      {/* --- the advisory tools --- */}
      <Text style={styles.prompt}>{t('home.chooseFeature')}</Text>
      <View style={styles.cards}>
        {FEATURES.map((f) => (
          <FeatureCard
            key={f.key}
            emoji={f.emoji}
            title={t(`features.${f.key}.title`)}
            description={t(`features.${f.key}.desc`)}
            onPress={() => router.push(f.route)}
          />
        ))}
      </View>

      {signedIn && farmer && (
        <Pressable style={styles.signOutRow} onPress={() => void signOut()}>
          <Text style={styles.signOutText}>
            {t('login.signedInAs', { phone: farmer.phone })} · {t('login.signOut')}
          </Text>
        </Pressable>
      )}

      <BackendSetting />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 18,
  },
  headerText: { flex: 1, paddingRight: 12 },
  greeting: { fontSize: 28, fontWeight: '800', color: Colors.primaryDark },
  tagline: { fontSize: 16, color: Colors.textMuted, marginTop: 4 },

  sectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  sectionTitle: { fontSize: 20, fontWeight: '800', color: Colors.text },
  addLink: { fontSize: 15, fontWeight: '700', color: Colors.primary },

  loginCard: {
    backgroundColor: '#EDF5EC',
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
  },
  loginTitle: { fontSize: 17, fontWeight: '800', color: Colors.primaryDark },
  loginBody: { fontSize: 15, color: Colors.text, marginTop: 6, lineHeight: 22 },

  emptyCard: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    borderStyle: 'dashed',
    borderRadius: 14,
    padding: 18,
    marginBottom: 16,
  },
  emptyTitle: { fontSize: 17, fontWeight: '800', color: Colors.text },
  emptyBody: { fontSize: 15, color: Colors.textMuted, marginTop: 6, lineHeight: 22 },
  spinner: { marginVertical: 20 },
  retryBtn: {
    marginTop: 12,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
  },
  retryText: { color: Colors.white, fontSize: 15, fontWeight: '700' },

  prompt: { fontSize: 18, fontWeight: '700', color: Colors.text, marginTop: 10, marginBottom: 14 },
  cards: {},

  signOutRow: { marginTop: 16, alignItems: 'center', paddingVertical: 8 },
  signOutText: { fontSize: 13, color: Colors.textMuted },
});
