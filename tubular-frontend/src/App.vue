<script setup>
import { ref, computed, shallowReadonly, shallowRef } from 'vue'

import Homepage from './components/Homepage.vue';
import Pipelines from './components/Pipelines.vue';
import PipelineHistory from './components/PipelineHistory.vue';
import Nodes from './components/Nodes.vue';
import NotFound from './components/NotFound.vue';

const menuItems = shallowRef([
  { route: "#/", title: "Home", page: Homepage },
  { route: "#/pipelines", title: "Pipelines", page: Pipelines },
  { route: "#/nodes", title: "Nodes", page: Nodes },
])

var routes = {
  "/view_pipeline": PipelineHistory
}

function makeRoutes(item)
{
  routes[item.route.slice(1)] = item.page;
}

menuItems.value.forEach(makeRoutes);

const currentPath = ref(window.location.hash)
let currentPathArgs = {}

window.addEventListener('hashchange', () =>
{
  let temp = window.location.hash.split("?", 1)

  currentPath.value = temp[0]

  console.log(currentPath.value)
  currentPathArgs = {}
  if (temp.length > 1)
  {
    let argStrs = temp[1].split("&")
    for (let arg in argStrs)
    {
      let argV = arg.split("=", 1)
      currentPathArgs[argV[0]] = argV[1]
    }
  }
})

const currentView = computed(() =>
{
  return routes[currentPath.value.slice(1) || '/'] || NotFound
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
