import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { Colors } from '@/constants/colors';
import { LOCATIONS } from '@/constants/locations';
import type { Location as District } from '@/constants/locations';
import { GpsError, getCurrentFix } from '@/services/location/gps';
import { useFarm } from '@/store/useFarm';

// Shared "where is this farm" control for weather, irrigation and mandi prices.
//
// One component because the three screens must never disagree about the farm's position, and
// because the GPS-vs-district fallback logic is fiddly enough that three copies would drift.
//
// GPS is offered, never forced: a denied permission or a failed fix silently leaves the farmer
// on their picked district, which always works offline.

export default function LocationBar() {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language === 'en';

  const farm = useFarm();
  const coords = useFarm((s) => s.coords());

  const [pickerOpen, setPickerOpen] = useState(false);
  const [locating, setLocating] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const locate = async () => {
    setLocating(true);
    setProblem(null);
    try {
      farm.setGps(await getCurrentFix());
    } catch (error) {
      const reason = error instanceof GpsError ? error.reason : 'error';
      setProblem(t(`gps.${reason}`));
    } finally {
      setLocating(false);
    }
  };

  return (
    <View>
      <View style={styles.row}>
        <View style={styles.flex1}>
          <Text style={styles.place}>📍 {coords.label}</Text>
          <Text style={styles.sub}>
            {coords.fromGps
              ? `${t('gps.using')}${
                  farm.gps?.accuracyM
                    ? ` · ${t('gps.accuracy', { m: Math.round(farm.gps.accuracyM) })}`
                    : ''
                }`
              : t('weatherScreen.district')}
          </Text>
        </View>
        <Pressable style={styles.changeBtn} onPress={() => setPickerOpen(true)}>
          <Text style={styles.changeText}>{t('weatherScreen.changeDistrict')}</Text>
        </Pressable>
      </View>

      {!coords.fromGps && (
        <Pressable style={styles.gpsBtn} onPress={() => void locate()} disabled={locating}>
          {locating ? (
            <View style={styles.inline}>
              <ActivityIndicator size="small" color={Colors.primaryDark} />
              <Text style={styles.gpsText}>{t('gps.locating')}</Text>
            </View>
          ) : (
            <Text style={styles.gpsText}>{t('gps.use')}</Text>
          )}
        </Pressable>
      )}

      {coords.fromGps && (
        <Pressable style={styles.linkBtn} onPress={farm.clearGps}>
          <Text style={styles.linkText}>{t('gps.useDistrict')}</Text>
        </Pressable>
      )}

      {problem && <Text style={styles.problem}>{problem}</Text>}

      <DistrictPicker
        open={pickerOpen}
        selectedId={farm.locationId}
        isEn={isEn}
        onClose={() => setPickerOpen(false)}
        onPick={(id) => {
          // Picking a district is an explicit override, so GPS steps aside.
          farm.update({ locationId: id, useGps: false });
          setPickerOpen(false);
        }}
      />
    </View>
  );
}

function DistrictPicker({
  open,
  selectedId,
  isEn,
  onClose,
  onPick,
}: {
  open: boolean;
  selectedId: string;
  isEn: boolean;
  onClose: () => void;
  onPick: (id: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal visible={open} animationType="slide" transparent onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
          <Text style={styles.sheetTitle}>{t('weatherScreen.selectDistrict')}</Text>
          <FlatList<District>
            data={LOCATIONS}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => {
              const selected = item.id === selectedId;
              return (
                <Pressable
                  style={[styles.districtRow, selected && styles.districtRowSelected]}
                  onPress={() => onPick(item.id)}
                >
                  <Text style={[styles.districtText, selected && styles.districtTextSelected]}>
                    {isEn ? item.en : item.mr}
                  </Text>
                  {selected && <Text style={styles.tick}>✓</Text>}
                </Pressable>
              );
            }}
          />
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex1: { flex: 1 },
  inline: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  place: { fontSize: 18, fontWeight: '800', color: Colors.text },
  sub: { fontSize: 13, color: Colors.textMuted, marginTop: 2 },
  changeBtn: { paddingVertical: 6, paddingHorizontal: 10 },
  changeText: { fontSize: 15, color: Colors.primary, fontWeight: '700' },

  gpsBtn: {
    marginTop: 8,
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 11,
    alignItems: 'center',
    backgroundColor: '#EDF5EC',
  },
  gpsText: { fontSize: 15, fontWeight: '700', color: Colors.primaryDark },
  linkBtn: { marginTop: 8, alignItems: 'center', paddingVertical: 6 },
  linkText: { fontSize: 14, color: Colors.textMuted, textDecorationLine: 'underline' },
  problem: {
    marginTop: 8,
    fontSize: 14,
    color: Colors.text,
    backgroundColor: '#FFF8E1',
    borderLeftWidth: 4,
    borderLeftColor: Colors.accent,
    borderRadius: 10,
    padding: 12,
    lineHeight: 21,
  },

  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: Colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingTop: 18,
    paddingHorizontal: 16,
    maxHeight: '75%',
  },
  sheetTitle: { fontSize: 19, fontWeight: '800', color: Colors.text, marginBottom: 12 },
  districtRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 15,
    paddingHorizontal: 14,
    borderRadius: 12,
    marginBottom: 6,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  districtRowSelected: { borderColor: Colors.primary, backgroundColor: '#EDF5EC' },
  districtText: { fontSize: 17, color: Colors.text },
  districtTextSelected: { fontWeight: '700', color: Colors.primaryDark },
  tick: { fontSize: 18, color: Colors.primary, fontWeight: '800' },
});
