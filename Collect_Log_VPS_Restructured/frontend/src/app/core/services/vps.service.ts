import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { VPS, VPSCreate, VPSUpdate, CollectResult, AnalyzeResult } from '../models/models';

@Injectable({ providedIn: 'root' })
export class VpsService {
  private base = `${environment.apiUrl}/vps`;

  constructor(private http: HttpClient) {}

  /** GET /api/vps/ */
  getAll(): Observable<VPS[]> {
    return this.http.get<VPS[]>(`${this.base}/`).pipe(catchError(this.handleError));
  }

  /** GET /api/vps/:id */
  getById(id: number): Observable<VPS> {
    return this.http.get<VPS>(`${this.base}/${id}`).pipe(catchError(this.handleError));
  }

  /** POST /api/vps/ */
  create(payload: VPSCreate): Observable<VPS> {
    return this.http.post<VPS>(`${this.base}/`, payload).pipe(catchError(this.handleError));
  }

  /** PUT /api/vps/:id */
  update(id: number, payload: VPSUpdate): Observable<VPS> {
    return this.http.put<VPS>(`${this.base}/${id}`, payload).pipe(catchError(this.handleError));
  }

  /** DELETE /api/vps/:id */
  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`).pipe(catchError(this.handleError));
  }

  /** POST /api/collect/:vps_id */
  collect(vpsId: number): Observable<CollectResult> {
    return this.http
      .post<CollectResult>(`${environment.apiUrl}/collect/${vpsId}`, {})
      .pipe(catchError(this.handleError));
  }

  /** POST /api/analyze/:vps_id */
  analyze(vpsId: number): Observable<AnalyzeResult> {
    return this.http
      .post<AnalyzeResult>(`${environment.apiUrl}/analyze/${vpsId}`, {})
      .pipe(catchError(this.handleError));
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let message = 'Une erreur inattendue est survenue.';
    if (error.status === 0) {
      message = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
    } else if (error.status === 404) {
      message = 'VPS introuvable.';
    } else if (error.status === 409) {
      message = error.error?.detail ?? 'Ce VPS existe déjà.';
    } else if (error.error?.detail) {
      message = error.error.detail;
    }
    return throwError(() => new Error(message));
  }
}