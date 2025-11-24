/**
 * Tests for ChatInterface.jsx - Main chat UI component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatInterface from './ChatInterface';

// Sample conversation data
const emptyConversation = {
  id: 'conv-1',
  title: 'Test Conversation',
  messages: [],
};

const conversationWithMessages = {
  id: 'conv-2',
  title: 'Active Conversation',
  messages: [
    { role: 'user', content: 'What is Python?' },
    {
      role: 'assistant',
      stage1: [{ model: 'openai/gpt-4o', response: 'Python is a programming language.' }],
      stage2: [
        {
          model: 'openai/gpt-4o',
          ranking: 'FINAL RANKING:\n1. Response A',
          parsed_ranking: ['Response A'],
        },
      ],
      stage3: { model: 'google/gemini-pro', response: 'Final answer about Python.' },
      metadata: {
        label_to_model: { 'Response A': 'openai/gpt-4o' },
        aggregate_rankings: [{ model: 'openai/gpt-4o', average_rank: 1.0, rankings_count: 1 }],
      },
    },
  ],
};

const conversationWithLoading = {
  id: 'conv-3',
  title: 'Loading Conversation',
  messages: [
    { role: 'user', content: 'Question' },
    {
      role: 'assistant',
      loading: { stage1: true },
    },
  ],
};

describe('ChatInterface', () => {
  let mockOnSendMessage;

  beforeEach(() => {
    mockOnSendMessage = vi.fn();
  });

  describe('empty states', () => {
    it('should show welcome message when no conversation', () => {
      render(
        <ChatInterface
          conversation={null}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByText('Welcome to LLM Council')).toBeInTheDocument();
      expect(
        screen.getByText('Create a new conversation to get started')
      ).toBeInTheDocument();
    });

    it('should show start message for empty conversation', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByText('Start a conversation')).toBeInTheDocument();
      expect(
        screen.getByText('Ask a question to consult the LLM Council')
      ).toBeInTheDocument();
    });

    it('should show input form for empty conversation', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByPlaceholderText(/Ask your question/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });
  });

  describe('message display', () => {
    it('should display user messages', () => {
      render(
        <ChatInterface
          conversation={conversationWithMessages}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByText('What is Python?')).toBeInTheDocument();
      expect(screen.getByText('You')).toBeInTheDocument();
    });

    it('should display assistant messages with stages', () => {
      render(
        <ChatInterface
          conversation={conversationWithMessages}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByText('LLM Council')).toBeInTheDocument();
      // Stage components should render
      expect(screen.getByText(/Stage 1/i)).toBeInTheDocument();
      expect(screen.getByText(/Stage 2/i)).toBeInTheDocument();
      expect(screen.getByText(/Final answer about Python/i)).toBeInTheDocument();
    });

    it('should show loading spinner for stage 1', () => {
      render(
        <ChatInterface
          conversation={conversationWithLoading}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(
        screen.getByText(/Running Stage 1: Collecting individual responses/i)
      ).toBeInTheDocument();
    });

    it('should show loading spinner for stage 2', () => {
      const convWithStage2Loading = {
        ...conversationWithLoading,
        messages: [
          { role: 'user', content: 'Question' },
          {
            role: 'assistant',
            stage1: [{ model: 'm1', response: 'r1' }],
            loading: { stage2: true },
          },
        ],
      };

      render(
        <ChatInterface
          conversation={convWithStage2Loading}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByText(/Running Stage 2: Peer rankings/i)).toBeInTheDocument();
    });

    it('should show loading spinner for stage 3', () => {
      const convWithStage3Loading = {
        ...conversationWithLoading,
        messages: [
          { role: 'user', content: 'Question' },
          {
            role: 'assistant',
            stage1: [{ model: 'm1', response: 'r1' }],
            stage2: [{ model: 'm1', ranking: 'r', parsed_ranking: [] }],
            loading: { stage3: true },
          },
        ],
      };

      render(
        <ChatInterface
          conversation={convWithStage3Loading}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByText(/Running Stage 3: Final synthesis/i)).toBeInTheDocument();
    });
  });

  describe('input handling', () => {
    it('should update input value on type', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, 'Hello world');

      expect(input).toHaveValue('Hello world');
    });

    it('should call onSendMessage when form is submitted', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, 'Test message');
      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
    });

    it('should clear input after sending', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, 'Test message');
      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(input).toHaveValue('');
    });

    it('should not send empty messages', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it('should not send whitespace-only messages', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, '   ');
      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it('should send on Enter key', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, 'Test message{Enter}');

      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
    });

    it('should not send on Shift+Enter (new line)', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2');

      expect(mockOnSendMessage).not.toHaveBeenCalled();
      // Input should contain newline
      expect(input.value).toContain('Line 1');
      expect(input.value).toContain('Line 2');
    });
  });

  describe('loading state', () => {
    it('should disable input when loading', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={true}
        />
      );

      expect(screen.getByPlaceholderText(/Ask your question/i)).toBeDisabled();
    });

    it('should disable send button when loading', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={true}
        />
      );

      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    it('should show loading indicator when loading', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={true}
        />
      );

      expect(screen.getByText(/Consulting the council/i)).toBeInTheDocument();
    });

    it('should not send message when loading', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={true}
        />
      );

      // Try to type and submit (input is disabled but let's ensure handler also checks)
      const input = screen.getByPlaceholderText(/Ask your question/i);
      // fireEvent bypasses disabled state for testing
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.submit(input.closest('form'));

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });
  });

  describe('send button state', () => {
    it('should disable send button when input is empty', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    it('should enable send button when input has content', async () => {
      const user = userEvent.setup();

      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const input = screen.getByPlaceholderText(/Ask your question/i);
      await user.type(input, 'Test');

      expect(screen.getByRole('button', { name: /send/i })).not.toBeDisabled();
    });
  });

  describe('markdown rendering', () => {
    it('should render markdown in user messages', () => {
      const convWithMarkdown = {
        id: 'conv-md',
        title: 'Markdown Test',
        messages: [{ role: 'user', content: 'Hello **world**' }],
      };

      render(
        <ChatInterface
          conversation={convWithMarkdown}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      // ReactMarkdown should convert **world** to <strong>
      const strongElement = screen.getByText('world');
      expect(strongElement.tagName).toBe('STRONG');
    });
  });

  describe('scroll behavior', () => {
    it('should call scrollIntoView when conversation changes', () => {
      const { rerender } = render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      // scrollIntoView is mocked in setup.js
      const scrollCalls = Element.prototype.scrollIntoView.mock.calls.length;

      // Rerender with new conversation
      rerender(
        <ChatInterface
          conversation={conversationWithMessages}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(Element.prototype.scrollIntoView.mock.calls.length).toBeGreaterThan(
        scrollCalls
      );
    });
  });

  describe('textarea attributes', () => {
    it('should have correct placeholder text', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      expect(
        screen.getByPlaceholderText(
          /Ask your question.*Shift\+Enter for new line.*Enter to send/i
        )
      ).toBeInTheDocument();
    });

    it('should have 3 rows by default', () => {
      render(
        <ChatInterface
          conversation={emptyConversation}
          onSendMessage={mockOnSendMessage}
          isLoading={false}
        />
      );

      const textarea = screen.getByPlaceholderText(/Ask your question/i);
      expect(textarea).toHaveAttribute('rows', '3');
    });
  });
});
