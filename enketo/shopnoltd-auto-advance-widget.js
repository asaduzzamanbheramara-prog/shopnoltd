import Widget from 'enketo-core/src/js/widget';

const APPEARANCE_PREFIX = 'shopnoltd-auto-';
const ALLOWED_KEYS = new Set([
    'Backspace',
    'Delete',
    'ArrowLeft',
    'ArrowRight',
    'ArrowUp',
    'ArrowDown',
    'Home',
    'End',
    'Tab',
    'Enter',
    'Escape',
]);

function beep() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const context = window.__shopnoltdBeepContext || (window.__shopnoltdBeepContext = new AudioContext());
        if (context.state === 'suspended') context.resume().catch(() => {});
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.value = 880;
        gain.gain.setValueAtTime(0.0001, context.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.12, context.currentTime + 0.005);
        gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.075);
        oscillator.connect(gain);
        gain.connect(context.destination);
        oscillator.start();
        oscillator.stop(context.currentTime + 0.08);
    } catch {
        // Audio is an enhancement; never block data entry when the browser denies audio.
    }
}

function shortName(input) {
    return (input?.name || input?.getAttribute('data-name') || '').split('/').pop();
}

function visible(element) {
    if (!element || element.disabled || element.readOnly) return false;
    const question = element.closest('.question');
    if (!question || question.classList.contains('disabled')) return false;
    const style = window.getComputedStyle(question);
    return style.display !== 'none' && style.visibility !== 'hidden' && question.getClientRects().length > 0;
}

function findInputByName(form, name) {
    return [...form.querySelectorAll('input:not(.ignore), textarea:not(.ignore), select:not(.ignore)')]
        .find((candidate) => shortName(candidate) === name && visible(candidate));
}

function nextQuestionInput(question) {
    const questions = [...question.closest('form.or').querySelectorAll('.question')];
    const index = questions.indexOf(question);
    for (const candidateQuestion of questions.slice(index + 1)) {
        const candidate = candidateQuestion.querySelector(
            'input:not(.ignore):not([type="hidden"]), textarea:not(.ignore), select:not(.ignore)'
        );
        if (visible(candidate)) return candidate;
    }
    return null;
}

export default class ShopnoltdAutoAdvance extends Widget {
    static get selector() {
        return '.or-appearance-shopnoltd-auto-1, .or-appearance-shopnoltd-auto-2, .or-appearance-shopnoltd-auto-3';
    }

    _init() {
        this.input = this.element.querySelector(
            'input:not(.ignore):not([type="hidden"]), textarea:not(.ignore)'
        );
        if (!this.input) return;

        const appearance = this.props.appearances.find((value) => value.startsWith(APPEARANCE_PREFIX));
        this.requiredLength = Number(appearance?.substring(APPEARANCE_PREFIX.length)) || 1;
        this.input.maxLength = this.requiredLength;
        this.input.setAttribute('inputmode', 'numeric');
        this.input.setAttribute('autocomplete', 'off');

        this.onKeyDown = (event) => {
            if (
                event.ctrlKey ||
                event.metaKey ||
                event.altKey ||
                ALLOWED_KEYS.has(event.key)
            ) return;
            if (!/^[0-9]$/.test(event.key)) event.preventDefault();
        };

        this.onInput = () => {
            const digits = this.input.value.replace(/[^0-9]/g, '').slice(0, this.requiredLength);
            if (this.input.value !== digits) this.input.value = digits;
            if (digits.length !== this.requiredLength) return;

            beep();
            const name = shortName(this.input);
            let targetName = null;

            const q4a = /^(setb_)?q4a_(\d+)$/.exec(name);
            const q4b = /^(setb_)?q4b_(\d+)$/.exec(name);
            if (q4a && digits === '0') {
                targetName = `${q4a[1] || ''}q4b_${q4a[2]}`;
            } else if (q4b && digits === '0') {
                targetName = `${q4b[1] || ''}q5`;
            }

            const target = targetName
                ? findInputByName(this.element.closest('form.or'), targetName)
                : nextQuestionInput(this.question);

            if (target) {
                window.setTimeout(() => {
                    target.focus();
                    if (typeof target.select === 'function') target.select();
                }, 0);
            }
        };

        this.input.addEventListener('keydown', this.onKeyDown);
        this.input.addEventListener('input', this.onInput);
    }

    disable() {
        if (this.input) this.input.disabled = true;
    }

    enable() {
        if (this.input) this.input.disabled = false;
    }

    update() {
        if (this.input) this.input.maxLength = this.requiredLength;
    }

    cleanup() {
        if (!this.input) return;
        this.input.removeEventListener('keydown', this.onKeyDown);
        this.input.removeEventListener('input', this.onInput);
    }
}
