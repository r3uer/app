import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import Markdown from 'react-native-markdown-display';
import { SafeAreaView } from 'react-native-safe-area-context';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export default function Index() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  // Request microphone permissions on mount
  useEffect(() => {
    (async () => {
      try {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          Alert.alert('Permission Required', 'Microphone permission is needed for voice input');
        }
      } catch (error) {
        console.error('Error requesting permissions:', error);
      }
    })();
  }, []);

  const startRecording = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Error', 'Failed to start recording. Please try again.');
    }
  };

  const stopRecording = async () => {
    try {
      if (!recording) return;

      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);

      if (uri) {
        // Note: Speech-to-text requires additional setup
        // For now, prompt user to type instead
        Alert.alert(
          'Voice Input',
          'Please type your question in the text box below. Full speech-to-text requires additional setup.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      Alert.alert('Error', 'Failed to process recording.');
    }
  };

  const sendQuestion = async (question: string) => {
    if (!question.trim()) return;

    setIsProcessing(true);
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setTextInput('');

    try {
      const response = await axios.post(`${EXPO_PUBLIC_BACKEND_URL}/api/ask`, {
        question: question,
        conversation_id: conversationId,
      });

      const assistantMessage: Message = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.answer,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setConversationId(response.data.conversation_id);

      // Scroll to bottom
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error) {
      console.error('Error sending question:', error);
      Alert.alert('Error', 'Failed to get response. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setTextInput('');
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Kotlin & Android Assistant</Text>
          <TouchableOpacity
            onPress={startNewConversation}
            style={styles.newChatButton}
          >
            <Ionicons name="add-circle-outline" size={28} color="#007AFF" />
          </TouchableOpacity>
        </View>

        {/* Messages */}
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
        >
          {messages.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="mic-outline" size={64} color="#666" />
              <Text style={styles.emptyText}>Ask me anything about DSA!</Text>
              <Text style={styles.emptySubtext}>
                Tap the microphone or type your question
              </Text>
            </View>
          ) : (
            messages.map((message) => (
              <View
                key={message.id}
                style={[
                  styles.messageBubble,
                  message.role === 'user'
                    ? styles.userBubble
                    : styles.assistantBubble,
                ]}
              >
                {message.role === 'assistant' ? (
                  <Markdown style={markdownStyles}>{message.content}</Markdown>
                ) : (
                  <Text style={styles.messageText}>{message.content}</Text>
                )}
              </View>
            ))
          )}
          {isProcessing && (
            <View style={[styles.messageBubble, styles.assistantBubble]}>
              <ActivityIndicator size="small" color="#007AFF" />
              <Text style={styles.processingText}>Thinking...</Text>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            placeholder="Type your question..."
            placeholderTextColor="#999"
            value={textInput}
            onChangeText={setTextInput}
            multiline
            maxLength={500}
            editable={!isProcessing}
          />
          <TouchableOpacity
            style={[
              styles.micButton,
              isRecording && styles.micButtonRecording,
            ]}
            onPress={isRecording ? stopRecording : startRecording}
            disabled={isProcessing}
          >
            <Ionicons
              name={isRecording ? 'stop' : 'mic'}
              size={28}
              color="white"
            />
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.sendButton,
              (!textInput.trim() || isProcessing) && styles.sendButtonDisabled,
            ]}
            onPress={() => sendQuestion(textInput)}
            disabled={!textInput.trim() || isProcessing}
          >
            <Ionicons name="send" size={24} color="white" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#1C1C1E',
    borderBottomWidth: 1,
    borderBottomColor: '#2C2C2E',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFF',
  },
  newChatButton: {
    padding: 4,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 24,
    fontWeight: '600',
    color: '#FFF',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 16,
    color: '#666',
    marginTop: 8,
    textAlign: 'center',
  },
  messageBubble: {
    maxWidth: '85%',
    padding: 12,
    borderRadius: 16,
    marginBottom: 12,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#007AFF',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#1C1C1E',
  },
  messageText: {
    fontSize: 16,
    color: '#FFF',
    lineHeight: 22,
  },
  processingText: {
    fontSize: 14,
    color: '#999',
    marginLeft: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 12,
    backgroundColor: '#1C1C1E',
    borderTopWidth: 1,
    borderTopColor: '#2C2C2E',
  },
  textInput: {
    flex: 1,
    minHeight: 44,
    maxHeight: 100,
    backgroundColor: '#2C2C2E',
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: '#FFF',
    fontSize: 16,
    marginRight: 8,
  },
  micButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#007AFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  micButtonRecording: {
    backgroundColor: '#FF3B30',
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#34C759',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#2C2C2E',
  },
});

const markdownStyles = {
  body: {
    color: '#FFF',
    fontSize: 16,
    lineHeight: 22,
  },
  code_inline: {
    backgroundColor: '#2C2C2E',
    color: '#34C759',
    paddingHorizontal: 4,
    paddingVertical: 2,
    borderRadius: 4,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  code_block: {
    backgroundColor: '#2C2C2E',
    padding: 12,
    borderRadius: 8,
    marginVertical: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 14,
  },
  fence: {
    backgroundColor: '#2C2C2E',
    padding: 12,
    borderRadius: 8,
    marginVertical: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 14,
    color: '#34C759',
  },
  heading1: {
    color: '#FFF',
    fontSize: 24,
    fontWeight: '700',
    marginVertical: 8,
  },
  heading2: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: '600',
    marginVertical: 6,
  },
  bullet_list: {
    marginVertical: 4,
  },
  ordered_list: {
    marginVertical: 4,
  },
  list_item: {
    color: '#FFF',
    marginVertical: 2,
  },
  link: {
    color: '#007AFF',
  },
};