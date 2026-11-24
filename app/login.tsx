import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { requestOtp } from '@/services/auth';
import { useAuth } from '@/store/useAuth';

// Phone-OTP login.
//
// Two honesty points the screen must carry:
//  * No SMS provider is wired, so it never says "check your SMS". The backend returns
//    `otp_is_real: false` plus the dev OTP, and we show exactly that.
//  * Login is only needed for the crop twin. "नंतर करा" leaves the farmer on the advisory
//    screens, which work fine signed out — asking for a phone number before showing value is
//    the fastest way to lose someone.

export default function LoginScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { signIn, busy } = useAuth();

  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [hint, setHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const phoneValid = /^[6-9]\d{9}$/.test(phone.replace(/\D/g, '').slice(-10));

  const send = async () => {
    setSending(true);
    setError(null);
    try {
      const res = await requestOtp(phone);
      setHint(res.messageMr ?? null);
      if (res.devOtp) setOtp(res.devOtp);
      setStep('otp');
    } catch {
      setError(t('login.sendFailed'));
    } finally {
      setSending(false);
    }
  };

  const submit = async () => {
    setError(null);
    try {
      await signIn(phone, otp);
      router.back();
    } catch {
      setError(t('login.wrongOtp'));
    }
  };

  return (
    <ScreenContainer scroll={false}>
      <KeyboardAvoidingView
        style={styles.flex1}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>{t('login.title')}</Text>
          <Text style={styles.subtitle}>{t('login.why')}</Text>

          <Text style={styles.label}>{t('login.phone')}</Text>
          <TextInput
            value={phone}
            onChangeText={setPhone}
            editable={step === 'phone'}
            placeholder="98XXXXXXXX"
            placeholderTextColor={Colors.textMuted}
            keyboardType="phone-pad"
            maxLength={13}
            style={[styles.input, step !== 'phone' && styles.inputLocked]}
          />

          {step === 'phone' ? (
            <Pressable
              style={[styles.primaryBtn, (!phoneValid || sending) && styles.btnDisabled]}
              disabled={!phoneValid || sending}
              onPress={() => void send()}
            >
              {sending ? (
                <ActivityIndicator color={Colors.white} />
              ) : (
                <Text style={styles.primaryText}>{t('login.sendOtp')}</Text>
              )}
            </Pressable>
          ) : (
            <>
              {hint && <Text style={styles.hint}>{hint}</Text>}

              <Text style={styles.label}>{t('login.otp')}</Text>
              <TextInput
                value={otp}
                onChangeText={setOtp}
                placeholder="------"
                placeholderTextColor={Colors.textMuted}
                keyboardType="number-pad"
                maxLength={6}
                style={[styles.input, styles.otpInput]}
              />

              <Pressable
                style={[styles.primaryBtn, (otp.length < 4 || busy) && styles.btnDisabled]}
                disabled={otp.length < 4 || busy}
                onPress={() => void submit()}
              >
                {busy ? (
                  <ActivityIndicator color={Colors.white} />
                ) : (
                  <Text style={styles.primaryText}>{t('login.verify')}</Text>
                )}
              </Pressable>

              <Pressable style={styles.linkBtn} onPress={() => setStep('phone')}>
                <Text style={styles.linkText}>{t('login.changeNumber')}</Text>
              </Pressable>
            </>
          )}

          {error && <Text style={styles.error}>{error}</Text>}

          <Pressable style={styles.skipBtn} onPress={() => router.back()}>
            <Text style={styles.skipText}>{t('login.later')}</Text>
          </Pressable>

          <Text style={styles.privacy}>{t('login.privacy')}</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  flex1: { flex: 1 },
  scroll: { padding: 20, paddingTop: 40 },
  title: { fontSize: 28, fontWeight: '800', color: Colors.primaryDark },
  subtitle: { fontSize: 16, color: Colors.textMuted, marginTop: 8, lineHeight: 24 },
  label: { fontSize: 15, color: Colors.textMuted, marginTop: 26, marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 20,
    color: Colors.text,
    letterSpacing: 1,
  },
  inputLocked: { backgroundColor: Colors.bg, color: Colors.textMuted },
  otpInput: { letterSpacing: 8, textAlign: 'center', fontSize: 24 },
  primaryBtn: {
    marginTop: 20,
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.45 },
  primaryText: { color: Colors.white, fontSize: 17, fontWeight: '800' },
  hint: {
    marginTop: 16,
    fontSize: 15,
    color: Colors.text,
    backgroundColor: '#FFF8E1',
    borderLeftWidth: 4,
    borderLeftColor: Colors.accent,
    borderRadius: 10,
    padding: 14,
    lineHeight: 22,
  },
  linkBtn: { marginTop: 14, alignItems: 'center', paddingVertical: 8 },
  linkText: { fontSize: 15, color: Colors.primary, fontWeight: '600' },
  error: { marginTop: 16, fontSize: 15, color: Colors.danger, fontWeight: '600' },
  skipBtn: { marginTop: 28, alignItems: 'center', paddingVertical: 10 },
  skipText: { fontSize: 16, color: Colors.textMuted, textDecorationLine: 'underline' },
  privacy: { marginTop: 24, fontSize: 13, color: Colors.textMuted, lineHeight: 20, textAlign: 'center' },
});
