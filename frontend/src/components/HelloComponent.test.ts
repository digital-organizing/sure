import HelloComponent from "./HelloComponent.vue";
import { mount } from '@vue/test-utils'
import { expect, test } from 'vitest'

test("renders properly", () => {
    const wrapper = mount(HelloComponent, { props: { name: "Test" } });
    expect(wrapper.text()).toContain("Hello from HelloComponent.vue!");
    expect(wrapper.text()).toContain("Test");

});