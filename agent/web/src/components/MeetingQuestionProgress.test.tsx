import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {MeetingQuestionProgress} from './MeetingQuestionProgress';
import type {SessionQuestionProgress} from '../lib/meetingSessions';

afterEach(cleanup);
const pending:SessionQuestionProgress={state:'pending',enabled:true,elapsed_seconds:2,delayed:false,attempt_id:7};

it('annonce le travail réel sans inventer de pourcentage ni désactiver une action',()=>{
  const {container}=render(<MeetingQuestionProgress status={pending}/>);
  expect(screen.getByRole('status',{name:'État des réponses automatiques'}).getAttribute('aria-busy')).toBe('true');
  expect(screen.getByText('Recherche automatique d’une réponse en cours…')).toBeTruthy();
  expect(container.querySelector('.async-activity-spinner')).toBeTruthy();
  expect(container.querySelector('[disabled]')).toBeNull();
});

it('signale le retard sans annuler ni recommencer le traitement',()=>{
  const {rerender}=render(<MeetingQuestionProgress status={pending}/>);
  rerender(<MeetingQuestionProgress status={{...pending,delayed:true,elapsed_seconds:30}}/>);
  expect(screen.getByText(/prend plus de temps/)).toBeTruthy();
  expect(screen.getByRole('status').getAttribute('aria-busy')).toBe('true');
});

it('ne conserve pas un indicateur actif lorsque la lecture serveur échoue',()=>{
  const {container}=render(<MeetingQuestionProgress status={pending} readError/>);
  expect(screen.getByText(/reste à vérifier/)).toBeTruthy();
  expect(screen.getByRole('status').getAttribute('aria-busy')).toBe('false');
  expect(container.querySelector('.async-activity-spinner')).toBeNull();
});

it.each(['idle','completed'] as const)('ne montre pas de faux travail pour un état %s',state=>{
  render(<MeetingQuestionProgress status={{...pending,state}}/>);
  expect(screen.queryByRole('status')).toBeNull();
});

it('accepte un ancien serveur sans état de progression',()=>{
  render(<MeetingQuestionProgress status={null}/>);
  expect(screen.queryByRole('status')).toBeNull();
});

it('ne promet pas une question manuelle lorsque la génération est indisponible',()=>{
  render(<MeetingQuestionProgress status={{...pending,delayed:true}} manualAvailable={false}/>);
  expect(screen.queryByText(/poser une question/)).toBeNull();
  expect(screen.getByText(/réponses conservées restent disponibles/)).toBeTruthy();
});

it.each(['failed','interrupted','obsolete','unknown','disabled'] as const)('présente %s sans simulation de traitement',state=>{
  const {container}=render(<MeetingQuestionProgress status={{...pending,state}}/>);
  expect(screen.getByRole('status').getAttribute('aria-busy')).toBe('false');
  expect(container.querySelector('.async-activity-spinner')).toBeNull();
});
