<script setup>
import { ref, computed, shallowRef } from 'vue'

import Homepage from './components/Homepage.vue';
import Pipelines from './components/Pipelines.vue';
import PipelineHistory from './components/PipelineHistory.vue';
import Nodes from './components/Nodes.vue';
import NotFound from './components/NotFound.vue';
import RunPipeline from './components/RunPipeline.vue';

import { Chart as ChartJS } from 'chart.js';

import parsePath from './path_utils.js';
import Archive from './components/Archive.vue';

// Setup default colors
ChartJS.defaults.color = "#FFF"

const menuItems = shallowRef([
  { route: "#/", title: "Home", page: Homepage },
  { route: "#/pipelines", title: "Pipelines", page: Pipelines },
  { route: "#/nodes", title: "Nodes", page: Nodes },
])

var routes = {
  "/view_pipeline": PipelineHistory,
  "/run_pipeline": RunPipeline,
  "/archive": Archive
}

function makeRoutes(item)
{
  routes[item.route.slice(1)] = item.page;
}

menuItems.value.forEach(makeRoutes);

const currentPath = ref(parsePath(window.location.hash, {}))

window.addEventListener('hashchange', () =>
{
  currentPath.value = parsePath(window.location.hash, {})
})

const currentView = computed(() =>
{
  let x = routes[currentPath.value] || NotFound
  if (x == NotFound)
  {
    console.log("path not found: '" + currentPath.value + "'")
  }
  return x
})

</script>

<template>
  <header>
    <meta name="viewport" content="width=device-width, initial-scale=1">
  </header>

  <main>
    <div id="layout">
      <!-- Menu toggle -->
      <a href="#menu" id="menuLink" class="menu-link">
        <!-- Hamburger icon -->
        <span></span>
      </a>

      <div id="menu">
        <div class="pure-menu">
          <a class="pure-menu-heading" href="#/">Tubular</a>

          <ul class="pure-menu-list">
            <li v-for="page in menuItems" class="pure-menu-item">
              <a :href="page.route" class="pure-menu-link">{{ page.title }}</a>
            </li>
          </ul>
        </div>
      </div>

      <div id="main">
        <div class="content">
          <component :is="currentView" />
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped></style>
