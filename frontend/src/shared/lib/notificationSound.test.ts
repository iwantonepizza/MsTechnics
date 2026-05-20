import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  _resetAudioContextForTests,
  isNotificationSoundEnabled,
  playNotificationSound,
  setNotificationSoundEnabled,
} from './notificationSound'

describe('notificationSound (T-7-012)', () => {
  let oscStartSpy: ReturnType<typeof vi.fn>
  let oscStopSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    localStorage.clear()
    _resetAudioContextForTests()

    oscStartSpy = vi.fn()
    oscStopSpy = vi.fn()

    // Минимальный mock AudioContext API.
    const oscillator = {
      type: 'sine',
      frequency: { value: 0 },
      connect: vi.fn(),
      start: oscStartSpy,
      stop: oscStopSpy,
    }
    const gain = {
      gain: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    }
    ;(globalThis as unknown as { AudioContext: unknown }).AudioContext = class {
      currentTime = 0
      destination = {}
      createOscillator() { return oscillator }
      createGain() { return gain }
    }
  })

  afterEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    delete (globalThis as unknown as Record<string, unknown>).AudioContext
  })

  it('default enabled = true when localStorage пуст', () => {
    expect(isNotificationSoundEnabled()).toBe(true)
  })

  it('setNotificationSoundEnabled(false) персистится и читается', () => {
    setNotificationSoundEnabled(false)
    expect(isNotificationSoundEnabled()).toBe(false)
    expect(localStorage.getItem('notificationSound.enabled')).toBe('0')

    setNotificationSoundEnabled(true)
    expect(isNotificationSoundEnabled()).toBe(true)
    expect(localStorage.getItem('notificationSound.enabled')).toBe('1')
  })

  it('playNotificationSound() запускает осциллятор, если включено', () => {
    playNotificationSound()
    expect(oscStartSpy).toHaveBeenCalledTimes(1)
    expect(oscStopSpy).toHaveBeenCalledTimes(1)
  })

  it('playNotificationSound() ничего не делает, если выключено', () => {
    setNotificationSoundEnabled(false)
    playNotificationSound()
    expect(oscStartSpy).not.toHaveBeenCalled()
  })

  it('playNotificationSound(force=true) играет даже если выключено', () => {
    setNotificationSoundEnabled(false)
    playNotificationSound(true)
    expect(oscStartSpy).toHaveBeenCalledTimes(1)
  })

  it('не падает, если AudioContext недоступен в окружении', () => {
    delete (globalThis as unknown as Record<string, unknown>).AudioContext
    _resetAudioContextForTests()
    expect(() => playNotificationSound(true)).not.toThrow()
  })
})
