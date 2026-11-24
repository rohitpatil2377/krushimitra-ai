import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { Colors } from '@/constants/colors';
import { apiUrl, builtInApiUrl, saveApiUrl } from '@/config';
import { getJson } from '@/services/api';

// Lets the farmer (or you, on a demo) point the app at a backend by hand.
//
// It exists because a standalone APK has no Metro host to derive the URL from, and a laptop's IP
// changes the moment you move to a hotspot. Without this, every IP change would mean another
// cloud rebuild. Collapsed by default so it never gets in a real user's way.

export default function BackendSetting() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(apiUrl);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  // Without this, a wrong address looks exactly like a working one: every screen just shows
  // "नमुना माहिती" and nothing says why. The check names the cause instead of leaving the
  // farmer (or you) guessing whether the server is down, the URL is stale, or the firewall
  // is blocking the phone.
  const test = async () => {
    setTesting(true);
    setResult(null);
    try {
      const h = await getJson<Record<string, unknown>>('/health');
      const real = ['vision', 'weather', 'market']
        .filter((k) => h[`${k}_is_real`] === true);
      setResult(
        real.length > 0
          ? t('serverSetting.okReal', { list: real.join(', ') })
          : t('serverSetting.okMock'),
      );
    } catch {
      setResult(t('serverSetting.unreachable'));
    } finally {
      setTesting(false);
    }
  };

  const apply = async (value: string | null) => {
    await saveApiUrl(value);
    setDraft(apiUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <View style={styles.wrap}>
      <Pressable onPress={() => setOpen((v) => !v)} style={styles.head}>
        <Text style={styles.headText}>
          ⚙️ {t('serverSetting.title')}
        </Text>
        <Text style={styles.status}>
          {apiUrl ? apiUrl.replace(/^https?:\/\//, '') : t('serverSetting.notSet')}
        </Text>
      </Pressable>

      {open && (
        <View style={styles.body}>
          <Text style={styles.help}>{t('serverSetting.help')}</Text>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder="http://192.168.1.5:8000"
            placeholderTextColor={Colors.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            style={styles.input}
          />
          <View style={styles.row}>
            <Pressable style={styles.saveBtn} onPress={() => void apply(draft)}>
              <Text style={styles.saveText}>{t('serverSetting.save')}</Text>
            </Pressable>
            <Pressable style={styles.resetBtn} onPress={() => void apply(null)}>
              <Text style={styles.resetText}>{t('serverSetting.reset')}</Text>
            </Pressable>
          </View>
          <Pressable style={styles.testBtn} onPress={() => void test()} disabled={testing}>
            {testing ? (
              <ActivityIndicator size="small" color={Colors.primaryDark} />
            ) : (
              <Text style={styles.testText}>{t('serverSetting.test')}</Text>
            )}
          </Pressable>

          {result && <Text style={styles.result}>{result}</Text>}
          {saved && <Text style={styles.savedNote}>✅ {t('serverSetting.saved')}</Text>}
          {builtInApiUrl ? (
            <Text style={styles.builtIn}>
              {t('serverSetting.builtIn', { url: builtInApiUrl })}
            </Text>
          ) : null}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 8,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 12,
    backgroundColor: Colors.card,
    overflow: 'hidden',
  },
  head: { paddingVertical: 12, paddingHorizontal: 14 },
  headText: { fontSize: 15, fontWeight: '700', color: Colors.text },
  status: { fontSize: 13, color: Colors.textMuted, marginTop: 2 },
  body: {
    paddingHorizontal: 14,
    paddingBottom: 14,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    paddingTop: 12,
  },
  help: { fontSize: 14, color: Colors.textMuted, lineHeight: 21, marginBottom: 10 },
  input: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: Colors.text,
    backgroundColor: Colors.bg,
  },
  row: { flexDirection: 'row', gap: 10, marginTop: 10 },
  saveBtn: {
    flex: 1,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 11,
    alignItems: 'center',
  },
  saveText: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  resetBtn: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 10,
    paddingVertical: 11,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  resetText: { color: Colors.text, fontSize: 15, fontWeight: '600' },
  savedNote: { fontSize: 14, color: Colors.primary, marginTop: 8, fontWeight: '600' },
  testBtn: {
    marginTop: 10,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
  },
  testText: { fontSize: 15, fontWeight: '700', color: Colors.primaryDark },
  result: { fontSize: 14, color: Colors.text, marginTop: 10, lineHeight: 21 },
  builtIn: { fontSize: 12, color: Colors.textMuted, marginTop: 8 },
});
