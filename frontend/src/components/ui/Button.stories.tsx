import type { Meta, StoryObj } from '@storybook/react'
import { Button } from './Button'
import { PenLine } from 'lucide-react'

const meta: Meta<typeof Button> = {
  title: 'Design System/Button',
  component: Button,
  argTypes: {
    onClick: { action: 'clicked' },
  },
  args: {
    children: 'Click me',
  },
}

type Story = StoryObj<typeof Button>

export const Primary: Story = {
  args: {
    variant: 'primary',
  },
}

export const Secondary: Story = {
  args: {
    variant: 'secondary',
  },
}

export const Outline: Story = {
  args: {
    variant: 'outline',
  },
}

export const Ghost: Story = {
  args: {
    variant: 'ghost',
  },
}

export const Danger: Story = {
  args: {
    variant: 'danger',
  },
}

export const WithIcon: Story = {
  args: {
    variant: 'primary',
    icon: <PenLine className="h-4 w-4" />,
    children: 'Edit Device',
  },
}

export const Loading: Story = {
  args: {
    variant: 'primary',
    loading: true,
    children: 'Saving...'
  },
}

export const Sizes: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <Button size="sm">Small</Button>
      <Button size="md">Medium</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
}

export default meta
