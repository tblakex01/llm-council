/**
 * Tests for api.js - API client for backend communication.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listConversations', () => {
    it('should fetch conversations from the API', async () => {
      const mockConversations = [
        { id: '1', title: 'Test', created_at: '2024-01-01', message_count: 0 },
      ];

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConversations),
      });

      const result = await api.listConversations();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/conversations'
      );
      expect(result).toEqual(mockConversations);
    });

    it('should throw error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });

      await expect(api.listConversations()).rejects.toThrow(
        'Failed to list conversations'
      );
    });

    it('should handle empty list', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      const result = await api.listConversations();

      expect(result).toEqual([]);
    });
  });

  describe('createConversation', () => {
    it('should create a new conversation', async () => {
      const mockConversation = {
        id: 'new-id',
        title: 'New Conversation',
        created_at: '2024-01-01',
        messages: [],
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConversation),
      });

      const result = await api.createConversation();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/conversations',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        }
      );
      expect(result).toEqual(mockConversation);
    });

    it('should throw error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });

      await expect(api.createConversation()).rejects.toThrow(
        'Failed to create conversation'
      );
    });
  });

  describe('getConversation', () => {
    it('should fetch a specific conversation', async () => {
      const mockConversation = {
        id: 'conv-123',
        title: 'Test Conv',
        messages: [{ role: 'user', content: 'Hello' }],
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConversation),
      });

      const result = await api.getConversation('conv-123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/conversations/conv-123'
      );
      expect(result).toEqual(mockConversation);
    });

    it('should throw error on 404', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      });

      await expect(api.getConversation('nonexistent')).rejects.toThrow(
        'Failed to get conversation'
      );
    });
  });

  describe('sendMessage', () => {
    it('should send a message to a conversation', async () => {
      const mockResponse = {
        stage1: [{ model: 'm1', response: 'r1' }],
        stage2: [{ model: 'm1', ranking: 'r' }],
        stage3: { model: 'm2', response: 'final' },
        metadata: {},
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.sendMessage('conv-123', 'Hello world');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/conversations/conv-123/message',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: 'Hello world' }),
        }
      );
      expect(result).toEqual(mockResponse);
    });

    it('should throw error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });

      await expect(api.sendMessage('conv-123', 'Hello')).rejects.toThrow(
        'Failed to send message'
      );
    });
  });

  describe('sendMessageStream', () => {
    it('should handle streaming response', async () => {
      const events = [];
      const mockEventData = [
        'data: {"type":"stage1_start"}\n\n',
        'data: {"type":"stage1_complete","data":[{"model":"m1","response":"r1"}]}\n\n',
        'data: {"type":"complete"}\n\n',
      ];

      // Create a mock readable stream
      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < mockEventData.length) {
            const chunk = new TextEncoder().encode(mockEventData[chunkIndex]);
            chunkIndex++;
            return Promise.resolve({ done: false, value: chunk });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      await api.sendMessageStream('conv-123', 'Hello', (type, event) => {
        events.push({ type, event });
      });

      expect(events).toHaveLength(3);
      expect(events[0].type).toBe('stage1_start');
      expect(events[1].type).toBe('stage1_complete');
      expect(events[2].type).toBe('complete');
    });

    it('should throw error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });

      await expect(
        api.sendMessageStream('conv-123', 'Hello', () => {})
      ).rejects.toThrow('Failed to send message');
    });

    it('should handle malformed JSON in stream', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const events = [];

      const mockEventData = [
        'data: not-valid-json\n\n',
        'data: {"type":"complete"}\n\n',
      ];

      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < mockEventData.length) {
            const chunk = new TextEncoder().encode(mockEventData[chunkIndex]);
            chunkIndex++;
            return Promise.resolve({ done: false, value: chunk });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      await api.sendMessageStream('conv-123', 'Hello', (type, event) => {
        events.push({ type, event });
      });

      // Should have logged error for malformed JSON
      expect(consoleSpy).toHaveBeenCalled();
      // Should still process valid event
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe('complete');

      consoleSpy.mockRestore();
    });

    it('should handle multi-chunk data', async () => {
      const events = [];

      // Split data across chunks to test buffering
      const mockEventData = [
        'data: {"type":"sta',
        'ge1_start"}\n\ndata: {"type":"complete"}\n\n',
      ];

      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < mockEventData.length) {
            const chunk = new TextEncoder().encode(mockEventData[chunkIndex]);
            chunkIndex++;
            return Promise.resolve({ done: false, value: chunk });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      // Note: Current implementation doesn't buffer across chunks
      // This test documents the current behavior
      await api.sendMessageStream('conv-123', 'Hello', (type, event) => {
        events.push({ type, event });
      });

      // Only complete event should be parsed (stage1_start is split)
      expect(events.some((e) => e.type === 'complete')).toBe(true);
    });

    it('should ignore non-data lines', async () => {
      const events = [];

      const mockEventData = [
        ': comment\n',
        'data: {"type":"complete"}\n\n',
        'event: ignore\n',
      ];

      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < mockEventData.length) {
            const chunk = new TextEncoder().encode(mockEventData[chunkIndex]);
            chunkIndex++;
            return Promise.resolve({ done: false, value: chunk });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      await api.sendMessageStream('conv-123', 'Hello', (type, event) => {
        events.push({ type, event });
      });

      // Only the data line should be processed
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe('complete');
    });
  });
});
