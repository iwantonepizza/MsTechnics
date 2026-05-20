/**
 * notificationSound — T-7-012 (A8 из owner-answers-2026-05-13).
 *
 * Короткий beep при определённых SSE-событиях (по умолчанию — новая заявка).
 * Юзер включает/выключает звук в Profile; preference хранится в localStorage.
 *
 * Используется Web Audio API (sine-beep) вместо <audio src=mp3>, чтобы:
 *   - не тащить аудиофайл в bundle/public;
 *   - не зависеть от автоплея mp3 (некоторые браузеры блокируют до user gesture).
 *
 * Web Audio API всё равно требует первого user gesture для resume() — но раз
 * юзер уже авторизован и кликал по UI до получения SSE-события, ограничение
 * на практике не мешает.
 */

const STORAGE_KEY = 'notificationSound.enabled'
const DEFAULT_ENABLED = true

let _audioCtx: AudioContext | null = null

/**
 * Прочитать текущее предпочтение пользователя.
 * Возвращает true по умолчанию (включено) если ничего не сохранено.
 */
export function isNotificationSoundEnabled(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return DEFAULT_ENABLED
    return raw === '1' || raw === 'true'
  } catch {
    return DEFAULT_ENABLED
  }
}

export function setNotificationSoundEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0')
  } catch {
    // private mode — игнор
  }
}

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (_audioCtx) return _audioCtx
  const Ctor =
    (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctor) return null
  try {
    _audioCtx = new Ctor()
    return _audioCtx
  } catch {
    return null
  }
}

/**
 * Сыграть короткий beep (~150 ms, 880 Hz, треугольный).
 * Респектирует preference юзера: если выключено — return без звука.
 *
 * @param force — игнорировать localStorage preference (для preview-кнопки в Profile).
 */
export function playNotificationSound(force: boolean = false): void {
  if (!force && !isNotificationSoundEnabled()) return

  const ctx = getAudioContext()
  if (!ctx) return

  try {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'triangle'
    osc.frequency.value = 880

    // attack / decay envelope чтобы не было щёлкания
    const now = ctx.currentTime
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.25, now + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(now)
    osc.stop(now + 0.18)
  } catch {
    // если AudioContext не resumed (нет user gesture) — игнор без падения
  }
}

/** Внутренний reset для тестов. */
export function _resetAudioContextForTests(): void {
  _audioCtx = null
}
