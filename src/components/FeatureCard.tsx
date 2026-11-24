import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Colors } from '@/constants/colors';

interface Props {
  emoji: string;
  title: string;
  description: string;
  onPress: () => void;
}

/** Large, tappable card for a feature on the Home screen. Big text + emoji = low-literacy friendly. */
export default function FeatureCard({ emoji, title, description, onPress }: Props) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={title}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <Text style={styles.emoji}>{emoji}</Text>
      <View style={styles.textWrap}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>
      </View>
      <Text style={styles.chevron}>›</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    // soft shadow (Android)
    elevation: 2,
  },
  pressed: {
    opacity: 0.7,
  },
  emoji: {
    fontSize: 40,
    marginRight: 16,
  },
  textWrap: {
    flex: 1,
  },
  title: {
    fontSize: 21,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 4,
  },
  description: {
    fontSize: 15,
    color: Colors.textMuted,
    lineHeight: 21,
  },
  chevron: {
    fontSize: 34,
    color: Colors.primary,
    marginLeft: 8,
  },
});
