import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Colors } from '@/constants/colors';
import { getChatService, type ChatMessage } from '@/services/chat';
import { getSpeechToText, tts } from '@/services/speech';
import { useChat } from '@/store/useChat';

export default function ChatScreen() {
  const { t } = useTranslation();
  const { messages, addMessage } = useChat();
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [listening, setListening] = useState(false);
  const listRef = useRef<FlatList<ChatMessage>>(null);

  async function send(rawText: string) {
    const text = rawText.trim();
    if (!text || thinking) return;

    addMessage('user', text);
    setInput('');
    setThinking(true);
    try {
      const history = useChat.getState().messages; // includes the message just added
      const reply = await getChatService().sendMessage(history, text);
      addMessage('assistant', reply);
    } catch {
      addMessage('assistant', t('chatScreen.error'));
    } finally {
      setThinking(false);
    }
  }

  async function onMicPress() {
    if (listening || thinking) return;
    setListening(true);
    try {
      const recognized = await getSpeechToText().transcribe();
      setInput(recognized); // farmer can review/edit before sending
    } catch {
      // ignore for now; real errors handled when Bhashini is wired
    } finally {
      setListening(false);
    }
  }

  const suggestions = t('chatScreen.suggestions', { returnObjects: true }) as unknown as string[];

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {messages.length === 0 ? (
          <EmptyState
            title={t('chatScreen.emptyTitle')}
            hint={t('chatScreen.emptyHint')}
            suggestions={suggestions}
            onPick={send}
          />
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            renderItem={({ item }) => (
              <MessageBubble message={item} readAloudLabel={t('chatScreen.readAloud')} />
            )}
            contentContainerStyle={styles.listContent}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
          />
        )}

        {thinking && <Text style={styles.statusText}>{t('chatScreen.thinking')}</Text>}
        {listening && <Text style={styles.statusText}>{t('chatScreen.listening')}</Text>}

        <View style={styles.inputBar}>
          <Pressable
            onPress={onMicPress}
            style={[styles.micButton, listening && styles.micButtonActive]}
            accessibilityLabel="microphone"
          >
            {listening ? <ActivityIndicator color={Colors.white} /> : <Text style={styles.micIcon}>🎤</Text>}
          </Pressable>

          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder={t('chatScreen.placeholder')}
            placeholderTextColor={Colors.textMuted}
            multiline
            onSubmitEditing={() => send(input)}
          />

          <Pressable
            onPress={() => send(input)}
            disabled={!input.trim() || thinking}
            style={[styles.sendButton, (!input.trim() || thinking) && styles.sendDisabled]}
            accessibilityLabel={t('chatScreen.send')}
          >
            <Text style={styles.sendIcon}>➤</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function EmptyState({
  title,
  hint,
  suggestions,
  onPick,
}: {
  title: string;
  hint: string;
  suggestions: string[];
  onPick: (text: string) => void;
}) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyHint}>{hint}</Text>
      <View style={styles.suggestions}>
        {suggestions.map((s) => (
          <Pressable key={s} style={styles.suggestionChip} onPress={() => onPick(s)}>
            <Text style={styles.suggestionText}>{s}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function MessageBubble({
  message,
  readAloudLabel,
}: {
  message: ChatMessage;
  readAloudLabel: string;
}) {
  const isUser = message.role === 'user';
  return (
    <View style={[styles.bubbleRow, isUser ? styles.rowRight : styles.rowLeft]}>
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.botBubble]}>
        <Text style={[styles.bubbleText, isUser ? styles.userText : styles.botText]}>
          {message.text}
        </Text>
        {!isUser && (
          <Pressable
            onPress={() => tts.speak(message.text)}
            style={styles.readAloud}
            accessibilityLabel={readAloudLabel}
          >
            <Text style={styles.readAloudText}>🔊 {readAloudLabel}</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  flex: { flex: 1 },
  listContent: { padding: 12, paddingBottom: 16 },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  emptyTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: Colors.primaryDark,
    textAlign: 'center',
    marginBottom: 10,
  },
  emptyHint: {
    fontSize: 16,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 23,
    marginBottom: 22,
  },
  suggestions: { gap: 10, width: '100%' },
  suggestionChip: {
    backgroundColor: Colors.white,
    borderWidth: 1.5,
    borderColor: Colors.primary,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  suggestionText: { fontSize: 16, color: Colors.primaryDark, fontWeight: '600', textAlign: 'center' },

  bubbleRow: { marginBottom: 10, flexDirection: 'row' },
  rowRight: { justifyContent: 'flex-end' },
  rowLeft: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '85%', borderRadius: 16, padding: 12 },
  userBubble: { backgroundColor: Colors.primary, borderBottomRightRadius: 4 },
  botBubble: {
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.border,
    borderBottomLeftRadius: 4,
  },
  bubbleText: { fontSize: 16, lineHeight: 24 },
  userText: { color: Colors.white },
  botText: { color: Colors.text },
  readAloud: { marginTop: 8, alignSelf: 'flex-start' },
  readAloudText: { fontSize: 14, fontWeight: '600', color: Colors.primary },

  statusText: {
    fontSize: 14,
    color: Colors.primary,
    paddingHorizontal: 16,
    paddingBottom: 4,
    fontStyle: 'italic',
  },

  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.card,
    gap: 8,
  },
  micButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  micButtonActive: { backgroundColor: Colors.danger },
  micIcon: { fontSize: 22 },
  input: {
    flex: 1,
    minHeight: 46,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 23,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    fontSize: 16,
    color: Colors.text,
    backgroundColor: Colors.bg,
  },
  sendButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendDisabled: { opacity: 0.4 },
  sendIcon: { fontSize: 20, color: Colors.white },
});
