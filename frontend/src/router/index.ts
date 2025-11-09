import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ConsultantView from '@/views/consultant/ConsultantView.vue'
import DashboardView from '@/views/consultant/DashboardView.vue'
import CaseView from '@/views/consultant/CaseView.vue'
import ConsultantQuestionnaire from '@/views/consultant/case/ConsultantQuestionnaire.vue'
import ClientQuestionnaire from '@/views/consultant/case/ClientQuestionnaire.vue'
import TestsView from '@/views/consultant/case/TestsView.vue'
import ResultView from '@/views/consultant/case/ResultView.vue'
import CommunicationView from '@/views/consultant/case/CommunicationView.vue'
import CaseHistory from '@/views/consultant/case/CaseHistory.vue'
import CreateCaseView from '@/views/consultant/CreateCaseView.vue'
import SupportView from '@/views/consultant/SupportView.vue'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: '/client-form',
      name: 'client-form',
      component: () => import('../views/ClientFormView.vue'),
    },
    {
     path: '/consultant',
     component: ConsultantView,
      children: [
        {
          path: '',
          name: 'consultant-dashboard',
          component: DashboardView,
        },
        {
          path: 'case/:caseId',
          name: 'consultant-case',
          component: CaseView,
          children: [
            {
              path: 'client-answers',
              name: 'consultant-case-client-answers',
              component: ClientQuestionnaire,
            },
            {
              path: 'consultant-questionnaire',
              component: ConsultantQuestionnaire,
            },
            {
              path: 'tests',
              component: TestsView,
            },
            {
              path: 'results',
              component: ResultView,
            },
            {
              path: 'communication',
              component: CommunicationView,
            },
            {
              path: 'history',
              component: CaseHistory,
            }
          ]
        },
        {
          path: 'new-case',
          name: 'consultant-new-case',
          component: CreateCaseView,
        },
        {
          path: 'support',
          name: 'consultant-support',
          component: SupportView,
        }
      ],
    }
  ],
})

export default router
