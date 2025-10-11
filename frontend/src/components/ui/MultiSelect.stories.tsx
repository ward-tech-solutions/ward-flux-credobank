import type { Meta, StoryObj } from '@storybook/react'
import { useState } from 'react'
import MultiSelect from './MultiSelect'

const options = ['Tbilisi', 'Imereti', 'Adjara', 'Samegrelo', 'Kakheti']

const meta: Meta<typeof MultiSelect> = {
  title: 'Design System/MultiSelect',
  component: MultiSelect,
  render: (args) => {
    const [selected, setSelected] = useState<string[]>(args.selected ?? [])
    return <MultiSelect {...args} selected={selected} onChange={setSelected} />
  },
  args: {
    label: 'Regions',
    placeholder: 'All regions',
    options,
    selected: ['Tbilisi', 'Imereti'],
  },
}

export default meta

type Story = StoryObj<typeof MultiSelect>

export const Default: Story = {}

export const Empty: Story = {
  args: {
    selected: [],
  },
}

export const LongList: Story = {
  args: {
    options: Array.from({ length: 20 }, (_, i) => `Branch ${i + 1}`),
    selected: ['Branch 1', 'Branch 5', 'Branch 10'],
    label: 'Branches',
    placeholder: 'Select branches',
  },
}
