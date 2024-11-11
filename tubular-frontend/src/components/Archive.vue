<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios';

import Tree from './Tree.vue';

import parsePath from '../path_utils.js';

let args = {}
parsePath(window.location.hash, args)

let tree = ref({})

function getArchiveFiles()
{
    axios.get("/api/archive_list?pipeline=" + args.pipeline + "&branch=" + args.branch + "&run=" + args.run)
        .then((response) =>
        {
            tree.value = response.data
        })
}

onMounted(() =>
{
    getArchiveFiles()
})

</script>

<template>
    <div>Archive</div>
    <Tree :treeData="tree" />
</template>