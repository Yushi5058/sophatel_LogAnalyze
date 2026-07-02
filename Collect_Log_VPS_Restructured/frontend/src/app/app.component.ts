import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  template: `
    <iframe
      class="frontend-frame"
      src="/assets/sophatel_nginx_v5_login.html"
      title="SOPHATEL Nginx Observability"
    ></iframe>
  `,
  styles: [`
    :host {
      display: block;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: #f0f4f8;
    }

    .frontend-frame {
      display: block;
      width: 100%;
      height: 100%;
      border: 0;
    }
  `]
})
export class AppComponent {}
