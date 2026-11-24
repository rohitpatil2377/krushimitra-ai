import * as ImagePicker from 'expo-image-picker';
import { ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import Button from '@/components/Button';
import ScreenContainer from '@/components/ScreenContainer';
import { Colors } from '@/constants/colors';
import { CROPS } from '@/constants/crops';
import { getDiseaseService, type DiseaseDiagnosis, type Severity } from '@/services/ai';
import { useDiagnosis } from '@/store/useDiagnosis';

export default function DiagnoseScreen() {
  const { t } = useTranslation();
  const { imageUri, cropId, result, setImage, setCrop, setResult, reset } = useDiagnosis();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze(uri: string, base64?: string) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const service = getDiseaseService();
      const diagnosis = await service.analyzeCropImage({
        uri,
        base64: base64 ?? undefined,
        cropId: cropId ?? undefined,
      });
      setResult(diagnosis);
    } catch {
      setError(t('diagnoseScreen.error'));
    } finally {
      setLoading(false);
    }
  }

  async function takePhoto() {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      setError(t('diagnoseScreen.permissionDenied'));
      return;
    }
    const res = await ImagePicker.launchCameraAsync({ base64: true, quality: 0.5 });
    if (!res.canceled) {
      const asset = res.assets[0];
      setImage(asset.uri);
      analyze(asset.uri, asset.base64 ?? undefined);
    }
  }

  async function chooseFromGallery() {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setError(t('diagnoseScreen.permissionDenied'));
      return;
    }
    const res = await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.5 });
    if (!res.canceled) {
      const asset = res.assets[0];
      setImage(asset.uri);
      analyze(asset.uri, asset.base64 ?? undefined);
    }
  }

  return (
    <ScreenContainer>
      <Text style={styles.intro}>{t('diagnoseScreen.intro')}</Text>

      {/* Crop selector */}
      <Text style={styles.sectionLabel}>{t('diagnoseScreen.selectCrop')}</Text>
      <View style={styles.chips}>
        {CROPS.map((crop) => {
          const selected = cropId === crop.id;
          return (
            <Pressable
              key={crop.id}
              onPress={() => setCrop(selected ? null : crop.id)}
              style={[styles.chip, selected && styles.chipSelected]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                {crop.emoji} {crop.mr}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* Photo preview */}
      {imageUri && <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="cover" />}

      {/* Actions */}
      <Button icon="📷" label={t('diagnoseScreen.takePhoto')} onPress={takePhoto} loading={loading} />
      <Button
        icon="🖼️"
        label={t('diagnoseScreen.chooseGallery')}
        variant="secondary"
        onPress={chooseFromGallery}
        disabled={loading}
      />

      {loading && <Text style={styles.loadingText}>{t('diagnoseScreen.analyzing')}</Text>}
      {error && <Text style={styles.errorText}>{error}</Text>}

      {result && !loading && (
        result.identified ? <ResultCard result={result} /> : <UnsureCard result={result} />
      )}

      {result && !loading && (
        <Button
          label={t('diagnoseScreen.retake')}
          variant="secondary"
          onPress={() => {
            reset();
            setError(null);
          }}
        />
      )}
    </ScreenContainer>
  );
}

/**
 * Shown when the model was not confident enough, or saw no crop.
 *
 * This card is the product promise made visible: no disease name presented as fact, no
 * treatment, no severity bar. Instead it explains why and tells the farmer how to get a usable
 * photo. A wrong diagnosis costs a farmer money and a crop, so "I'm not sure" is the correct
 * answer, not a failure state.
 */
function UnsureCard({ result }: { result: DiseaseDiagnosis }) {
  const { t } = useTranslation();

  return (
    <View style={[styles.card, styles.cardUnsure]}>
      {result.isMock && <Text style={styles.demoBadge}>{t('common.demoData')}</Text>}

      <Text style={styles.unsureEmoji}>🤔</Text>
      <Text style={styles.unsureTitle}>{result.diseaseName}</Text>
      {result.note && <Text style={styles.unsureNote}>{result.note}</Text>}
      <Text style={styles.paragraph}>{result.cause}</Text>

      {result.prevention.length > 0 && (
        <Section title={t('diagnoseScreen.howToPhoto')} color={Colors.primary}>
          {result.prevention.map((tip, i) => (
            <BulletLine key={i} text={tip} />
          ))}
        </Section>
      )}

      <Text style={styles.disclaimer}>{t('diagnoseScreen.disclaimer')}</Text>
    </View>
  );
}

/** Renders one confident diagnosis: name, severity, cause, treatment, prevention, feedback. */
function ResultCard({ result }: { result: DiseaseDiagnosis }) {
  const { t, i18n } = useTranslation();
  const confidenceLabel = {
    low: t('diagnoseScreen.confidenceLow'),
    medium: t('diagnoseScreen.confidenceMedium'),
    high: t('diagnoseScreen.confidenceHigh'),
  }[result.confidence];

  return (
    <View style={styles.card}>
      {result.isMock && <Text style={styles.demoBadge}>{t('common.demoData')}</Text>}

      <Text style={styles.diseaseName}>{result.diseaseName}</Text>
      {result.diseaseNameEn && <Text style={styles.diseaseNameEn}>{result.diseaseNameEn}</Text>}
      <Text style={styles.confidence}>
        {t('diagnoseScreen.confidence')}: {confidenceLabel} ({Math.round(result.confidenceScore * 100)}%)
      </Text>

      {/* An honest caveat (e.g. "telya is never fully cured") outranks the advice below it. */}
      {result.note && <Text style={styles.noteBox}>ℹ️ {result.note}</Text>}
      {!result.curable && <Text style={styles.notCurableBox}>⚠️ {t('diagnoseScreen.notCurable')}</Text>}

      {result.severity && <SeverityBlock severity={result.severity} />}

      <Section title={`🔍 ${t('diagnoseScreen.cause')}`} color={Colors.danger}>
        <Text style={styles.paragraph}>{result.cause}</Text>
      </Section>

      {result.treatment.length > 0 && (
        <Section title={`💊 ${t('diagnoseScreen.treatment')}`} color={Colors.primary}>
          {result.treatment.map((step, i) => (
            <BulletLine key={i} text={step} />
          ))}
        </Section>
      )}

      {/* The dosage disclaimer is deliberately a separate, unmissable block rather than one
          bullet among many. We name active ingredients but never a quantity — dose depends on
          formulation, crop stage and the local label, and a wrong number harms people. */}
      {result.doseNote && (
        <View style={styles.doseBox}>
          <Text style={styles.doseTitle}>{t('diagnoseScreen.doseTitle')}</Text>
          <Text style={styles.doseText}>{result.doseNote}</Text>
        </View>
      )}

      {/* English active ingredients: a shopkeeper reads the English label on the bottle. */}
      {result.chemicals.length > 0 && (
        <Section title={t('diagnoseScreen.askShop')} color={Colors.textMuted}>
          <View style={styles.chemRow}>
            {result.chemicals.map((chem) => (
              <Text key={chem} style={styles.chemChip}>
                {chem}
              </Text>
            ))}
          </View>
        </Section>
      )}

      {result.prevention.length > 0 && (
        <Section title={`🛡️ ${t('diagnoseScreen.prevention')}`} color={Colors.accent}>
          {result.prevention.map((tip, i) => (
            <BulletLine key={i} text={tip} />
          ))}
        </Section>
      )}

      {/* Provenance, in English only — it is the model's own wording, useful to an agronomist
          or to us when auditing, but noise for a Marathi-reading farmer. */}
      {result.symptoms && i18n.language === 'en' && (
        <Text style={styles.provenance}>
          👁️ {t('diagnoseScreen.modelSeen')}: {result.symptoms}
        </Text>
      )}

      {result.diagnosisId && <FeedbackRow result={result} />}

      <Text style={styles.disclaimer}>{t('diagnoseScreen.disclaimer')}</Text>
    </View>
  );
}

/**
 * "Was this right?" — the single most valuable thing the app collects.
 *
 * Public plant-disease datasets are lab photographs; models trained on them fall apart on real
 * phone pictures. Field photos carrying a farmer-confirmed label are the only fix, and they are
 * the asset no competitor can copy. Shown only when the backend returned a diagnosisId, so it
 * never appears on sample data.
 */
function FeedbackRow({ result }: { result: DiseaseDiagnosis }) {
  const { t } = useTranslation();
  const [state, setState] = useState<'idle' | 'sending' | 'done' | 'failed'>('idle');

  async function send(wasCorrect: boolean) {
    if (!result.diagnosisId) return;
    setState('sending');
    const ok = await getDiseaseService().submitFeedback({
      diagnosisId: result.diagnosisId,
      wasCorrect,
      correctDisease: undefined,
    });
    setState(ok ? 'done' : 'failed');
  }

  if (state === 'done') {
    return <Text style={styles.feedbackThanks}>🙏 {t('diagnoseScreen.feedbackThanks')}</Text>;
  }

  return (
    <View style={styles.feedbackBox}>
      <Text style={styles.feedbackQuestion}>{t('diagnoseScreen.feedbackQuestion')}</Text>
      <View style={styles.feedbackButtons}>
        <Pressable
          disabled={state === 'sending'}
          onPress={() => send(true)}
          style={[styles.feedbackBtn, styles.feedbackBtnYes]}
        >
          <Text style={styles.feedbackBtnText}>👍 {t('diagnoseScreen.feedbackYes')}</Text>
        </Pressable>
        <Pressable
          disabled={state === 'sending'}
          onPress={() => send(false)}
          style={[styles.feedbackBtn, styles.feedbackBtnNo]}
        >
          <Text style={styles.feedbackBtnText}>👎 {t('diagnoseScreen.feedbackNo')}</Text>
        </Pressable>
      </View>
      {state === 'failed' && (
        <Text style={styles.errorText}>{t('diagnoseScreen.feedbackFailed')}</Text>
      )}
    </View>
  );
}

function Section({
  title,
  color,
  children,
}: {
  title: string;
  color: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color }]}>{title}</Text>
      {children}
    </View>
  );
}

const SEVERITY_COLORS: Record<Severity['level'], string> = {
  healthy: '#2E7D32',
  mild: '#9E9D24',
  moderate: '#F9A825',
  severe: '#EF6C00',
  critical: '#C62828',
};

function SeverityBlock({ severity }: { severity: Severity }) {
  const { t, i18n } = useTranslation();
  const labelKey = {
    healthy: 'sevHealthy',
    mild: 'sevMild',
    moderate: 'sevModerate',
    severe: 'sevSevere',
    critical: 'sevCritical',
  }[severity.level];
  const color = SEVERITY_COLORS[severity.level];
  const pct = Math.round(severity.severityPct);

  return (
    <View style={[styles.severityBox, { borderColor: color }]}>
      <View style={styles.severityHeader}>
        <Text style={[styles.severityLevel, { color }]}>
          {t('diagnoseScreen.severity')}: {t(`diagnoseScreen.${labelKey}`)} · {pct}%
        </Text>
      </View>
      {/* simple severity bar */}
      <View style={styles.severityTrack}>
        <View
          style={[styles.severityFill, { width: `${pct}%` as `${number}%`, backgroundColor: color }]}
        />
      </View>
      <Text style={styles.severityAction}>
        ⏱️ {t('diagnoseScreen.action')}: {severity.recommendedAction}
      </Text>
      {severity.evidence && i18n.language === 'en' && (
        <Text style={styles.provenance}>
          📏 {t('diagnoseScreen.sevMeasured')}: {severity.evidence}
        </Text>
      )}
    </View>
  );
}

function BulletLine({ text }: { text: string }) {
  return (
    <View style={styles.bulletRow}>
      <Text style={styles.bulletDot}>•</Text>
      <Text style={styles.bulletText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  intro: {
    fontSize: 16,
    color: Colors.textMuted,
    lineHeight: 23,
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 10,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 18,
  },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 22,
    borderWidth: 1.5,
    borderColor: Colors.border,
    backgroundColor: Colors.white,
  },
  chipSelected: {
    borderColor: Colors.primary,
    backgroundColor: '#E8F3E6',
  },
  chipText: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.textMuted,
  },
  chipTextSelected: {
    color: Colors.primaryDark,
  },
  preview: {
    width: '100%',
    height: 220,
    borderRadius: 14,
    marginBottom: 8,
    backgroundColor: Colors.border,
  },
  loadingText: {
    fontSize: 16,
    color: Colors.primary,
    textAlign: 'center',
    marginTop: 8,
  },
  errorText: {
    fontSize: 16,
    color: Colors.danger,
    textAlign: 'center',
    marginTop: 8,
  },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 18,
    marginTop: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    elevation: 2,
  },
  cardUnsure: {
    borderColor: '#F9A825',
    borderWidth: 1.5,
    backgroundColor: '#FFFDF5',
  },
  unsureEmoji: {
    fontSize: 34,
    textAlign: 'center',
  },
  unsureTitle: {
    fontSize: 21,
    fontWeight: '800',
    color: Colors.text,
    textAlign: 'center',
    marginTop: 6,
    marginBottom: 10,
  },
  unsureNote: {
    fontSize: 16,
    fontWeight: '600',
    color: '#8D6E00',
    lineHeight: 24,
    marginBottom: 10,
  },
  demoBadge: {
    alignSelf: 'flex-start',
    fontSize: 13,
    fontWeight: '700',
    color: Colors.white,
    backgroundColor: Colors.accent,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 10,
  },
  diseaseName: {
    fontSize: 23,
    fontWeight: '800',
    color: Colors.text,
  },
  diseaseNameEn: {
    fontSize: 15,
    color: Colors.textMuted,
    marginTop: 2,
  },
  confidence: {
    fontSize: 15,
    color: Colors.textMuted,
    marginTop: 6,
    marginBottom: 4,
  },
  noteBox: {
    fontSize: 15,
    color: '#1F4E79',
    backgroundColor: '#EAF2FB',
    borderRadius: 10,
    padding: 11,
    lineHeight: 23,
    marginTop: 10,
  },
  notCurableBox: {
    fontSize: 15,
    fontWeight: '700',
    color: '#8D3A00',
    backgroundColor: '#FFF0E3',
    borderRadius: 10,
    padding: 11,
    lineHeight: 23,
    marginTop: 8,
  },
  severityBox: {
    marginTop: 14,
    borderWidth: 1.5,
    borderRadius: 12,
    padding: 12,
    backgroundColor: '#FFFDF7',
  },
  severityHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  severityLevel: {
    fontSize: 17,
    fontWeight: '800',
  },
  severityTrack: {
    height: 10,
    borderRadius: 5,
    backgroundColor: Colors.border,
    marginTop: 10,
    overflow: 'hidden',
  },
  severityFill: {
    height: '100%',
    borderRadius: 5,
  },
  severityAction: {
    fontSize: 15,
    color: Colors.text,
    lineHeight: 22,
    marginTop: 10,
  },
  doseBox: {
    marginTop: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#C62828',
    backgroundColor: '#FDECEC',
    padding: 12,
  },
  doseTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#8E1B1B',
    marginBottom: 6,
  },
  doseText: {
    fontSize: 15,
    color: '#5F1414',
    lineHeight: 23,
  },
  chemRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chemChip: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingHorizontal: 11,
    paddingVertical: 6,
    overflow: 'hidden',
  },
  section: {
    marginTop: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  paragraph: {
    fontSize: 16,
    color: Colors.text,
    lineHeight: 24,
  },
  bulletRow: {
    flexDirection: 'row',
    marginBottom: 6,
  },
  bulletDot: {
    fontSize: 16,
    color: Colors.text,
    marginRight: 8,
    lineHeight: 24,
  },
  bulletText: {
    flex: 1,
    fontSize: 16,
    color: Colors.text,
    lineHeight: 24,
  },
  provenance: {
    fontSize: 13,
    color: Colors.textMuted,
    fontStyle: 'italic',
    lineHeight: 19,
    marginTop: 10,
  },
  feedbackBox: {
    marginTop: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  feedbackQuestion: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 10,
  },
  feedbackButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  feedbackBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1.5,
    alignItems: 'center',
  },
  feedbackBtnYes: {
    borderColor: Colors.primary,
    backgroundColor: '#E8F3E6',
  },
  feedbackBtnNo: {
    borderColor: Colors.danger,
    backgroundColor: '#FDECEC',
  },
  feedbackBtnText: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text,
  },
  feedbackThanks: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.primaryDark,
    textAlign: 'center',
    marginTop: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    lineHeight: 24,
  },
  disclaimer: {
    fontSize: 13.5,
    color: Colors.textMuted,
    fontStyle: 'italic',
    marginTop: 18,
    lineHeight: 20,
  },
});
