import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span class="badge" [class]="badgeClass">{{ status }}</span>
  `,
  styles: [`
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .3px;
    }
    .ok    { background: #14532d; color: #86efac; }
    .redir { background: #1e3a5f; color: #93c5fd; }
    .client{ background: #451a03; color: #fdba74; }
    .server{ background: #7f1d1d; color: #fca5a5; }
    .unknown{ background: #1e293b; color: #94a3b8; }
  `]
})
export class StatusBadgeComponent {
  @Input() status: number | null = null;

  get badgeClass(): string {
    if (!this.status)          return 'unknown';
    if (this.status < 300)     return 'ok';
    if (this.status < 400)     return 'redir';
    if (this.status < 500)     return 'client';
    return 'server';
  }
}
