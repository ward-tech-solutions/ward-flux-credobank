import type { Meta, StoryObj } from '@storybook/react'
import Select, { type SelectOption } from './Select'

const meta: Meta<typeof Select> = {
  title: 'Design System/Select',
  component: Select,
  args: {
    label: 'Region',
    helperText: 'Choose a region to filter devices.',
    options: [
      { value: 'all', label: 'All Regions' },
      { value: 'tbilisi', label: 'Tbilisi' },
      { value: 'imereti', label: 'Imereti' },
      { value: 'kakheti', label: 'Kakheti' },
    ] as SelectOption[],
  },
  argTypes: {
    options: { control: { disable: true } },
  },
  parameters: {
    controls: { exclude: ['options'] },
  },
}

export default meta

type Story = StoryObj<typeof Select>

export const Default: Story = {
  args: {
    value: 'all',
  },
}

export const WithError: Story = {
  args: {
    value: 'all',
    error: 'Region is required.',
    helperText: undefined,
  },
}

export const Disabled: Story = {
  args: {
    disabled: true,
    value: 'all',
    helperText: 'Selection disabled while loading.',
  },
}
