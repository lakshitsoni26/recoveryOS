import { useState, useEffect, useRef, useCallback } from 'react';
import type { UseSpeechToTextOptions, UseSpeechToTextReturn } from '../types';

interface ISpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      length: number;
      [index: number]: {
        transcript: string;
      };
    };
  };
}

interface ISpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

interface ISpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onresult: ((event: ISpeechRecognitionEvent) => void) | null;
  onerror: ((event: ISpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface ISpeechRecognitionConstructor {
  new (): ISpeechRecognition;
}

export function useSpeechToText(options: UseSpeechToTextOptions = {}): UseSpeechToTextReturn {
  const { lang = 'en-IN' } = options;

  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isListeningRef = useRef<boolean>(false);
  const latestTranscriptRef = useRef<string>('');

  const optionsRef = useRef<UseSpeechToTextOptions>(options);
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const sendAudioToServer = useCallback(async (audioBlob: Blob): Promise<string> => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'mic_recording.webm');

      const resp = await fetch(`/api/transcribe?language=${encodeURIComponent(lang)}`, {
        method: 'POST',
        body: formData
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.transcript && data.transcript.trim()) {
          return data.transcript.trim();
        }
      }
    } catch (e) {
      console.warn('Server transcription exception:', e);
    }
    return '';
  }, [lang]);

  const stopListening = useCallback(() => {
    isListeningRef.current = false;
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    // 1. Stop Web Speech Recognition
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        try { recognitionRef.current.abort(); } catch {}
      }
    }

    // 2. Stop MediaRecorder and trigger server upload
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch {}
    }

    setIsListening(false);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const windowWithSpeech = window as unknown as {
      SpeechRecognition?: ISpeechRecognitionConstructor;
      webkitSpeechRecognition?: ISpeechRecognitionConstructor;
    };
    const SpeechRecognitionClass =
      windowWithSpeech.SpeechRecognition || windowWithSpeech.webkitSpeechRecognition;

    if (SpeechRecognitionClass) {
      try {
        const recognition = new SpeechRecognitionClass();
        recognition.lang = lang;
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          setIsListening(true);
          isListeningRef.current = true;
          setError(null);
        };

        recognition.onresult = (event: ISpeechRecognitionEvent) => {
          let interimText = '';
          let finalText = '';

          for (let i = 0; i < event.results.length; ++i) {
            const item = event.results[i];
            if (item && item[0]) {
              if (item.isFinal) {
                finalText += item[0].transcript + ' ';
              } else {
                interimText += item[0].transcript;
              }
            }
          }

          const fullCurrent = (finalText + interimText).trim();
          if (fullCurrent) {
            latestTranscriptRef.current = fullCurrent;
            setTranscript(fullCurrent);
            if (optionsRef.current.onTranscriptChange) {
              optionsRef.current.onTranscriptChange(fullCurrent);
            }

            // Auto-commit on natural silence after 2200ms
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current);
            }
            silenceTimerRef.current = setTimeout(() => {
              if (isListeningRef.current) {
                stopListening();
                if (optionsRef.current.onSpeechComplete) {
                  optionsRef.current.onSpeechComplete(latestTranscriptRef.current || fullCurrent);
                }
              }
            }, 2200);
          }
        };

        recognition.onerror = (event: ISpeechRecognitionErrorEvent) => {
          if (event.error === 'no-speech') return;
          if (event.error === 'not-allowed') {
            setError('Microphone permission was denied. Please allow microphone access in browser.');
          }
        };

        recognition.onend = () => {
          if (isListeningRef.current) {
            try { recognition.start(); } catch {}
          }
        };

        recognitionRef.current = recognition;
      } catch (e) {
        console.warn('SpeechRecognition setup notice:', e);
      }
    }

    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch {}
      }
    };
  }, [lang, stopListening]);

  const startListening = useCallback(async () => {
    // 1. Duck / Cancel active TTS output
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    }

    latestTranscriptRef.current = '';
    setTranscript('');
    audioChunksRef.current = [];
    isListeningRef.current = true;
    setIsListening(true);
    setError(null);

    // 2. Hardware Audio Stream via getUserMedia & MediaRecorder
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          if (audioBlob.size > 500) {
            const serverText = await sendAudioToServer(audioBlob);
            const finalText = serverText || latestTranscriptRef.current;
            if (finalText) {
              latestTranscriptRef.current = finalText;
              setTranscript(finalText);
              if (optionsRef.current.onSpeechComplete) {
                optionsRef.current.onSpeechComplete(finalText);
              }
            }
          }
        };

        mediaRecorder.start(250); // Slice chunks every 250ms
      }
    } catch (err) {
      console.warn('getUserMedia audio hardware acquisition error:', err);
    }

    // 3. Start Web Speech as live preview
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch {}
    }
  }, [sendAudioToServer]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      const currentText = latestTranscriptRef.current || transcript;
      stopListening();
      if (currentText && optionsRef.current.onSpeechComplete) {
        optionsRef.current.onSpeechComplete(currentText);
      }
    } else {
      void startListening();
    }
  }, [isListening, startListening, stopListening, transcript]);

  return {
    isListening,
    transcript,
    error,
    startListening,
    stopListening,
    toggleListening,
    setTranscript
  };
}

export default useSpeechToText;
