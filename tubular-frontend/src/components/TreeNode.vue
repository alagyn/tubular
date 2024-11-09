<template>
    <li class="node-tree">
        <div v-if="node.children && node.children.length">
            <span class="label">{{ node.label }}</span>

            <ul>
                <TreeNode v-for="child in node.children" :node="child"></TreeNode>
            </ul>
        </div>
        <a v-else href="#/TODO">{{ node.label }}</a>
    </li>
</template>

<script>
export default {
    props: {
        node: Object
    }
};
</script>