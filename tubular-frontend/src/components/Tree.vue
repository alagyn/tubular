<template>
    <div class="tree">
        <ul class="tree-list">
            <TreeNode :node="treeData"></TreeNode>
        </ul>
    </div>
</template>

<script>
import TreeNode from './TreeNode.vue';

export default {
    props: {
        treeData: Object
    },
    components: {
        TreeNode
    }
};
</script>

<style>
.tree-list ul {
    padding-left: 16px;
    margin: 6px 0;
}
</style>