/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Utility: FocusManager (Accessible Keyboard Navigation & Focus Trapping)
 *
 * Requirements & DoD:
 * - Every interactive element reachable and operable via keyboard alone.
 * - Manages modal drawer focus lifecycle: capture, focus-transfer, focus-trapping, and restoration.
 */

export class FocusManager {
  private previousFocus: HTMLElement | null = null;

  /**
   * Captures the currently active element before an overlay drawer opens.
   */
  public captureActiveFocus(): HTMLElement | null {
    if (
      typeof document !== 'undefined' &&
      document.activeElement &&
      (typeof HTMLElement === 'undefined' || document.activeElement instanceof HTMLElement)
    ) {
      this.previousFocus = document.activeElement as HTMLElement;
    }
    return this.previousFocus;
  }

  /**
   * Returns the currently stored previously focused element.
   */
  public getPreviousFocus(): HTMLElement | null {
    return this.previousFocus;
  }

  /**
   * Clears the stored previous focus reference.
   */
  public clearPreviousFocus(): void {
    this.previousFocus = null;
  }

  /**
   * Restores focus back to the previously active element if still in the DOM.
   */
  public restorePreviousFocus(): boolean {
    if (this.previousFocus && typeof this.previousFocus.focus === 'function') {
      try {
        if (typeof document !== 'undefined' && document.body?.contains(this.previousFocus)) {
          this.previousFocus.focus();
          this.previousFocus = null;
          return true;
        }
      } catch {
        // Suppress errors if element detached
      }
    }
    this.previousFocus = null;
    return false;
  }

  /**
   * Sets focus to the first focusable element or preferred element inside a container.
   */
  public focusInitial(container: HTMLElement, preferredSelector?: string): HTMLElement | null {
    if (preferredSelector) {
      const preferred = container.querySelector<HTMLElement>(preferredSelector);
      if (preferred && typeof preferred.focus === 'function') {
        preferred.focus();
        return preferred;
      }
    }

    const focusable = this.getFocusableElements(container);
    if (focusable.length > 0 && focusable[0]) {
      focusable[0].focus();
      return focusable[0];
    }

    if (typeof container.focus === 'function') {
      container.focus();
      return container;
    }

    return null;
  }

  /**
   * Traps Tab and Shift+Tab key navigation within a modal or drawer container.
   */
  public trapFocus(container: HTMLElement, e: KeyboardEvent): boolean {
    if (e.key !== 'Tab') return false;

    const focusable = this.getFocusableElements(container);
    if (focusable.length === 0) return false;

    const firstElement = focusable[0];
    const lastElement = focusable[focusable.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === firstElement || document.activeElement === container) {
        e.preventDefault();
        lastElement?.focus();
        return true;
      }
    } else {
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
        return true;
      }
    }

    return false;
  }

  /**
   * Retrieves all visible, operable focusable elements within a container.
   */
  public getFocusableElements(container: HTMLElement): HTMLElement[] {
    const selector = [
      'button:not([disabled])',
      '[href]',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ].join(', ');

    return Array.from(container.querySelectorAll<HTMLElement>(selector)).filter(el => {
      return el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0 || el.tabIndex >= 0;
    });
  }
}

export const focusManager = new FocusManager();
