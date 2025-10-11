import type { Meta, StoryObj } from '@storybook/react'
import Input from './Input'
import { Search, User, Lock } from 'lucide-react'

const meta: Meta<typeof Input> = {
  title: 'Design System/Input',
  component: Input,
  args: {
    label: 'Username',
    placeholder: 'Enter username',
  },
}

type Story = StoryObj<typeof Input>

export const Default: Story = {}

export const WithIcon: Story = {
  args: {
    icon: <User className="h-4 w-4" />,
  },
}

export const Password: Story = {
  args: {
    type: 'password',
    label: 'Password',
    placeholder: '••••••••',
    icon: <Lock className="h-4 w-4" />,
  },
}

export const ErrorState: Story = {
  args: {
    error: 'Invalid username supplied.',
  },
}

export const WithHelper: Story = {
  args: {
    helperText: 'Use 8+ characters with letters and numbers.',
  },
}

export const SearchField: Story = {
  render: () => (
    <div className="max-w-sm">
      <Input icon={<Search className="h-4 w-4" />} placeholder="Search devices..." />
    </div>
  ),
}

export default meta
