import type { Meta, StoryObj } from '@storybook/react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './Card'
import { Button } from './Button'

const meta: Meta<typeof Card> = {
  title: 'Design System/Card',
  component: Card,
  args: {
    variant: 'default',
    hover: false,
    children: (
      <>
        <CardHeader>
          <CardTitle>Active Alerts</CardTitle>
          <CardDescription>Monitor live incidents across all regions.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-neutral-600 dark:text-neutral-300">
            No active alerts detected. Systems operating within normal thresholds.
          </div>
        </CardContent>
        <CardFooter>
          <Button size="sm" variant="ghost">View History</Button>
          <Button size="sm" variant="primary">Create Alert Rule</Button>
        </CardFooter>
      </>
    )
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'glass', 'bordered'],
    },
    hover: {
      control: 'boolean',
    },
  },
}

type Story = StoryObj<typeof Card>

export const Default: Story = {}

export const Glass: Story = {
  args: {
    variant: 'glass',
  },
}

export const Bordered: Story = {
  args: {
    variant: 'bordered',
  },
}

export const WithHover: Story = {
  args: {
    hover: true,
  },
}

export const MetricCard: Story = {
  render: () => (
    <Card hover className="max-w-sm">
      <CardHeader>
        <CardDescription>Uptime</CardDescription>
        <CardTitle className="text-3xl text-primary-500">99.97%</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          +0.12% compared to last week
        </p>
      </CardContent>
      <CardFooter>
        <Button variant="ghost" size="sm">View report</Button>
      </CardFooter>
    </Card>
  ),
}

export default meta
