/**
 * Tests for Stage2.jsx - Peer Rankings component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Stage2 from './Stage2';

// Sample test data
const sampleRankings = [
  {
    model: 'openai/gpt-4o',
    ranking: `Response A provides detailed analysis.
Response B is comprehensive but verbose.

FINAL RANKING:
1. Response B
2. Response A`,
    parsed_ranking: ['Response B', 'Response A'],
  },
  {
    model: 'anthropic/claude-3-opus',
    ranking: `Both responses are good.

FINAL RANKING:
1. Response A
2. Response B`,
    parsed_ranking: ['Response A', 'Response B'],
  },
];

const sampleLabelToModel = {
  'Response A': 'openai/gpt-4o',
  'Response B': 'anthropic/claude-3-opus',
};

const sampleAggregateRankings = [
  { model: 'openai/gpt-4o', average_rank: 1.5, rankings_count: 2 },
  { model: 'anthropic/claude-3-opus', average_rank: 1.5, rankings_count: 2 },
];

describe('Stage2', () => {
  describe('rendering', () => {
    it('should render null when rankings is empty', () => {
      const { container } = render(<Stage2 rankings={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it('should render null when rankings is undefined', () => {
      const { container } = render(<Stage2 rankings={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('should render stage title', () => {
      render(<Stage2 rankings={sampleRankings} />);
      expect(screen.getByText('Stage 2: Peer Rankings')).toBeInTheDocument();
    });

    it('should render tabs for each ranking model', () => {
      render(<Stage2 rankings={sampleRankings} />);

      // Should show short model names in tabs
      expect(screen.getByRole('button', { name: 'gpt-4o' })).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'claude-3-opus' })
      ).toBeInTheDocument();
    });

    it('should render full model name in content', () => {
      render(<Stage2 rankings={sampleRankings} />);
      expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    });

    it('should render aggregate rankings when provided', () => {
      render(
        <Stage2
          rankings={sampleRankings}
          aggregateRankings={sampleAggregateRankings}
        />
      );

      expect(
        screen.getByText('Aggregate Rankings (Street Cred)')
      ).toBeInTheDocument();
      // Both models have the same average rank, so use getAllByText
      expect(screen.getAllByText('Avg: 1.50')).toHaveLength(2);
      expect(screen.getAllByText('(2 votes)')).toHaveLength(2);
    });

    it('should not render aggregate rankings when empty', () => {
      render(<Stage2 rankings={sampleRankings} aggregateRankings={[]} />);

      expect(
        screen.queryByText('Aggregate Rankings (Street Cred)')
      ).not.toBeInTheDocument();
    });
  });

  describe('tab interaction', () => {
    it('should show first tab content by default', () => {
      render(<Stage2 rankings={sampleRankings} />);

      // First model's content should be visible
      expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    });

    it('should switch content when clicking tabs', () => {
      render(<Stage2 rankings={sampleRankings} />);

      // Click second tab
      fireEvent.click(screen.getByRole('button', { name: 'claude-3-opus' }));

      // Second model's full name should now be in the content area
      expect(screen.getByText('anthropic/claude-3-opus')).toBeInTheDocument();
    });

    it('should highlight active tab', () => {
      render(<Stage2 rankings={sampleRankings} />);

      const firstTab = screen.getByRole('button', { name: 'gpt-4o' });
      const secondTab = screen.getByRole('button', { name: 'claude-3-opus' });

      // First tab should be active initially
      expect(firstTab).toHaveClass('active');
      expect(secondTab).not.toHaveClass('active');

      // Click second tab
      fireEvent.click(secondTab);

      expect(firstTab).not.toHaveClass('active');
      expect(secondTab).toHaveClass('active');
    });
  });

  describe('de-anonymization', () => {
    it('should replace Response labels with model names in bold', () => {
      render(
        <Stage2 rankings={sampleRankings} labelToModel={sampleLabelToModel} />
      );

      // The de-anonymized text should contain bolded model names
      // ReactMarkdown converts **text** to <strong> tags
      const strongElements = screen.getAllByText('gpt-4o');
      expect(strongElements.length).toBeGreaterThan(0);
    });

    it('should handle missing labelToModel gracefully', () => {
      render(<Stage2 rankings={sampleRankings} />);

      // Should still render without errors
      expect(screen.getByText('Stage 2: Peer Rankings')).toBeInTheDocument();
    });
  });

  describe('parsed rankings display', () => {
    it('should show extracted ranking section', () => {
      render(
        <Stage2 rankings={sampleRankings} labelToModel={sampleLabelToModel} />
      );

      expect(screen.getByText('Extracted Ranking:')).toBeInTheDocument();
    });

    it('should display parsed rankings as ordered list', () => {
      render(
        <Stage2 rankings={sampleRankings} labelToModel={sampleLabelToModel} />
      );

      // Check that the parsed ranking is displayed
      const listItems = screen
        .getByText('Extracted Ranking:')
        .closest('.parsed-ranking')
        .querySelectorAll('li');
      expect(listItems.length).toBe(2);
    });

    it('should de-anonymize parsed rankings', () => {
      render(
        <Stage2 rankings={sampleRankings} labelToModel={sampleLabelToModel} />
      );

      // The parsed ranking should show model names, not labels
      const parsedRanking = screen
        .getByText('Extracted Ranking:')
        .closest('.parsed-ranking');

      // Should show short model names in the list
      expect(parsedRanking.textContent).toContain('claude-3-opus');
    });

    it('should show original label if model not in mapping', () => {
      const rankingsWithUnknown = [
        {
          model: 'test/model',
          ranking: 'test',
          parsed_ranking: ['Response X'],
        },
      ];

      render(
        <Stage2
          rankings={rankingsWithUnknown}
          labelToModel={sampleLabelToModel}
        />
      );

      // Unknown label should be shown as-is
      expect(screen.getByText('Response X')).toBeInTheDocument();
    });

    it('should not show parsed ranking section if empty', () => {
      const rankingsNoParsed = [
        {
          model: 'test/model',
          ranking: 'Some text without ranking',
          parsed_ranking: [],
        },
      ];

      render(<Stage2 rankings={rankingsNoParsed} />);

      expect(screen.queryByText('Extracted Ranking:')).not.toBeInTheDocument();
    });
  });

  describe('aggregate rankings', () => {
    it('should show position numbers', () => {
      render(
        <Stage2
          rankings={sampleRankings}
          aggregateRankings={sampleAggregateRankings}
        />
      );

      expect(screen.getByText('#1')).toBeInTheDocument();
      expect(screen.getByText('#2')).toBeInTheDocument();
    });

    it('should show model short names', () => {
      render(
        <Stage2
          rankings={sampleRankings}
          aggregateRankings={sampleAggregateRankings}
        />
      );

      // In aggregate rankings section
      const aggregateSection = screen
        .getByText('Aggregate Rankings (Street Cred)')
        .closest('.aggregate-rankings');
      expect(aggregateSection.textContent).toContain('gpt-4o');
    });

    it('should format average rank to 2 decimal places', () => {
      const rankings = [
        { model: 'test/model', average_rank: 1.333333, rankings_count: 3 },
      ];

      render(
        <Stage2 rankings={sampleRankings} aggregateRankings={rankings} />
      );

      expect(screen.getByText('Avg: 1.33')).toBeInTheDocument();
    });

    it('should show rankings count', () => {
      const rankings = [
        { model: 'test/model', average_rank: 1.5, rankings_count: 5 },
      ];

      render(
        <Stage2 rankings={sampleRankings} aggregateRankings={rankings} />
      );

      expect(screen.getByText('(5 votes)')).toBeInTheDocument();
    });
  });

  describe('explanatory text', () => {
    it('should show explanation about anonymization', () => {
      render(<Stage2 rankings={sampleRankings} />);

      expect(
        screen.getByText(/anonymized as Response A, B, C/i)
      ).toBeInTheDocument();
    });

    it('should show explanation about bold formatting', () => {
      render(<Stage2 rankings={sampleRankings} />);

      expect(screen.getByText(/bold/i)).toBeInTheDocument();
    });
  });

  describe('model name extraction', () => {
    it('should handle models without slashes', () => {
      const rankingsNoSlash = [
        {
          model: 'simple-model',
          ranking: 'test',
          parsed_ranking: ['Response A'],
        },
      ];

      render(<Stage2 rankings={rankingsNoSlash} />);

      // Should show the full name when no slash present
      expect(
        screen.getByRole('button', { name: 'simple-model' })
      ).toBeInTheDocument();
    });

    it('should extract part after slash', () => {
      const rankingsWithSlash = [
        {
          model: 'provider/model-name',
          ranking: 'test',
          parsed_ranking: [],
        },
      ];

      render(<Stage2 rankings={rankingsWithSlash} />);

      expect(
        screen.getByRole('button', { name: 'model-name' })
      ).toBeInTheDocument();
    });
  });
});

// Test the deAnonymizeText function directly
describe('deAnonymizeText', () => {
  // Import the function from the module
  // Note: Since it's not exported, we test it indirectly through component behavior
  // For direct testing, the function would need to be exported

  it('should replace all occurrences of a label', () => {
    const rankings = [
      {
        model: 'test/model',
        ranking:
          'Response A is good. Response A also has depth. Response B is okay.',
        parsed_ranking: [],
      },
    ];
    const labelToModel = {
      'Response A': 'openai/gpt-4',
      'Response B': 'anthropic/claude',
    };

    render(<Stage2 rankings={rankings} labelToModel={labelToModel} />);

    // Multiple occurrences should all be replaced
    const content = screen.getByText(/is good/i).closest('.ranking-content');
    // The markdown should contain the model names bolded
    expect(content.innerHTML).toContain('gpt-4');
  });
});
