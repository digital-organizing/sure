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
import CaseHistoryView from '@/views/consultant/case/CaseHistoryView.vue'
import CreateCaseView from '@/views/consultant/CreateCaseView.vue'
import SupportView from '@/views/consultant/SupportView.vue'
import AboutView from '@/views/AboutView.vue'
import PrivacyView from '@/views/PrivacyView.vue'
import ClientWelcomeView from '@/views/ClientWelcomeView.vue'
import ClientFormView from '@/views/ClientFormView.vue'
import ClientPhoneNumberView from '@/views/ClientPhoneNumberView.vue'
import ClientDoneView from '@/views/ClientDoneView.vue'
import ClientResultView from '@/views/ClientResultView.vue'
import AccountView from '@/views/user/AccountView.vue'
import LoginView from '@/views/user/LoginView.vue'
import LogoutView from '@/views/user/LogoutView.vue'
import SetupView from '@/views/user/SetupView.vue'
import Setup2FaView from '@/views/user/Setup2FaView.vue'
import CaseSummaryView from '@/views/consultant/case/CaseSummaryView.vue'

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
      component: AboutView,
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: PrivacyView,
    },
    {
      path: '/client/:caseId',
      name: 'client-start',
      component: ClientWelcomeView,
      props: true,
      meta: {
        showInternalMenu: false,
      },
    },
    {
      path: '/client/:caseId/form',
      name: 'client-form',
      component: ClientFormView,
      props: true,
      meta: {
        showInternalMenu: false,
      },
    },
    {
      path: '/client/:caseId/phone',
      name: 'client-phone',
      component: ClientPhoneNumberView,
      props: true,
      meta: {
        showInternalMenu: false,
      },
    },
    {
      path: '/client/:caseId/done',
      name: 'client-done',
      component: ClientDoneView,
      props: (route) => ({
        caseId: route.params.caseId as string,
        showCaseId: route.query.showCaseId === 'true',
      }),
      meta: {
        showInternalMenu: false,
      },
    },
    {
      path: '/results',
      name: 'results',
      component: ClientResultView,
      meta: {
        showInternalMenu: false,
      },
    },
    {
      path: '/account',
      name: 'account',
      component: AccountView,
      children: [
        {
          path: '/login',
          name: 'login',
          component: LoginView,
          meta: {
            doNotRedirectToLogin: true,
          },
        },
        {
          path: '/logout',
          name: 'logout',
          component: LogoutView,
        },
        {
          path: '/setup',
          name: 'setup',
          component: SetupView,
          meta: {
            doNotRedirectToLogin: true,
          },
        },
        {
          path: '/setup-2fa',
          name: 'setup-2fa',
          component: Setup2FaView,
        },
      ],
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
          props: true,
          children: [
            {
              path: 'client-answers',
              name: 'consultant-client-answers',
              component: ClientQuestionnaire,
            },
            {
              path: 'consultant-questionnaire',
              name: 'consultant-questionnaire',
              component: ConsultantQuestionnaire,
            },
            {
              path: 'tests',
              name: 'consultant-tests',
              component: TestsView,
              props: true,
            },
            {
              path: 'summary',
              name: 'consultant-case-summary',
              component: CaseSummaryView,
              props: true,
            },
            {
              path: 'results',
              component: ResultView,
              name: 'consultant-results',

              props: true,
            },
            {
              path: 'communication',
              name: 'consultant-communication',
              component: CommunicationView,
              props: true,
            },
            {
              path: 'history',
              name: 'consultant-case-history',
              component: CaseHistoryView,
              props: true,
            },
          ],
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
        },
      ],
    },
  ],
})

export default router
