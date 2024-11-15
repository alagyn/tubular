<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios';

import parsePath from '../path_utils.js';
import { pipelineStatuses } from '../enums.js';

let args = {}
parsePath(window.location.hash, args)

const stages = ref([])

function getStages()
{
    axios.get("/api/run?pipeline=" + args.pipeline + "&run=" + args.run).then(
        (res) =>
        {
            stages.value = res.data
            console.log(stages.value)
        }
    )
}

onMounted(() =>
{
    getStages()
})



</script>

<template>
    <div>View Run {{ args.run }}</div>

    <a :href="`#/archive?pipeline=${args.pipeline}&branch=${args.branch}&run=${args.run}`"
        class="pure-button">Archive</a>
    <a :href="`#/output?pipeline=${args.pipeline}&branch=${args.branch}&run=${args.run}`" class="pure-button">Output</a>

    <div>
        <div v-for="stage in stages">
            {{ stage.display }}
            <div class="indent" v-for="task in stage.stages">
                {{ task.display }}: {{ pipelineStatuses[task.status] }}
            </div>
        </div>

    </div>

</template>

<style>
.indent {
    margin-left: 40px;
}
</style>