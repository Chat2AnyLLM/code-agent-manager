import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Providers } from './Providers'

describe('Providers page', () => {
  it('lists and adds providers', async () => {
    render(<Providers />)
    expect(await screen.findByText('local')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/provider name/i), { target: { value: 'new-provider' } })
    fireEvent.change(screen.getByLabelText(/provider endpoint/i), { target: { value: 'http://localhost:5000/v1' } })
    fireEvent.click(screen.getByRole('button', { name: /add provider/i }))

    expect(await screen.findByText('new-provider')).toBeInTheDocument()
  })
})
