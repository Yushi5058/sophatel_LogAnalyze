import { Component } from '@angular/core';

@Component({
  selector: 'app-logs',
  standalone: true,          // requis en Angular 17 pour utiliser `imports`
  imports: [],
  templateUrl: './logs.html',
  styleUrl: './logs.css',
})
export class Logs {

}
