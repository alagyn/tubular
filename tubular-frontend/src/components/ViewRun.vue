<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios';

import parsePath from '../path_utils.js';
import { STATUS_TO_NAME, STATUS_TO_STYLE } from '../enums.js';

let args = {}
parsePath(window.location.hash, args)

const meta = ref([])

function getStages()
{
    axios.get("/api/run?pipeline=" + args.pipeline + "&run=" + args.run).then(
        (res) =>
        {
            meta.value = res.data
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

    <div>
        <a :href="`#/archive?pipeline=${args.pipeline}&branch=${args.branch}&run=${args.run}`"
            class="pure-button">Archive: {{ meta.numArchived }} items</a>
    </div>


    <!--
    <a :href="`#/output?pipeline=${args.pipeline}&branch=${args.branch}&run=${args.run}`" class="pure-button">Output</a>
    -->

    <div>
        <div v-for="stage in meta.stages">
            {{ stage.display }}
            <div class="indent pure-g" v-for="task in stage.stages">
                <div class="pure-u-1-2 pure-g task-box ">
                    <div class="pure-u-1-2">
                        <a class="pure-button output-button"
                            :href="`/api/output?pipeline=${args.pipeline}&branch=${args.branch}&run=${args.run}&file=${task.output}`">{{
                                task.display }}</a>
                    </div>
                    <div class="pure-u-1-2">
                        <span :class="STATUS_TO_STYLE[task.status] + ' status'">{{ STATUS_TO_NAME[task.status] }}</span>
                    </div>
                </div>
            </div>
        </div>

    </div>

</template>

<style>
.task-box {
    border: 1px;
    border-color: black;
    border-style: solid;
    border-radius: 5px;
    margin: 5px 0px 0px 40px;
}

.output-button {
    background: var(--main-highlight);
    color: white;
    padding: 2px 4px;
    margin: 4px;
    box-sizing: border-box;
    width: 100%;
}

.status {
    justify-items: center;
    display: grid;
}
</style>