<script setup lang=js>
import { ref, onMounted } from 'vue'
import NodeDoughnut from './graphs/NodeDoughnut.vue';
import PrevRunsDoughnut from './graphs/PrevRunsDoughnut.vue';
import Pipelines from './Pipelines.vue';


</script>

<template>
    <div>Homepage</div>

    <div class="pure-g">
        <div class="pure-u-1-2">
            <NodeDoughnut />
        </div>
        <div class="pure-u-1-2">
            <PrevRunsDoughnut />
        </div>
    </div>
    <div>
        <Pipelines />
    </div>

</template>