import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'logs',
    loadComponent: () =>
      import('./features/logs/logs').then(m => m.Logs)
  },
  {
    path: 'vps',
    loadComponent: () =>
      import('./features/vps/vps.component').then(m => m.VpsComponent)
  },
  { path: '**', redirectTo: 'dashboard' }
];
