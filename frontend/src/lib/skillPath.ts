// skill 名称只在作者内唯一，所以凡是定位某一个 skill 的地方都必须带上用户名。
// 用户名虽然服务端已经限制了字符集，这里仍然 encode —— 以后放宽限制时不会坏。
function seg(value: string) {
  return encodeURIComponent(value)
}

/** 详情页地址：/skills/<username>/<name> */
export function skillPath(username: string, name: string) {
  return `/skills/${seg(username)}/${seg(name)}`
}

/** API 地址：/api/skills/<username>/<name><suffix>，suffix 形如 '/download' */
export function skillApiPath(username: string, name: string, suffix = '') {
  return `/api/skills/${seg(username)}/${seg(name)}${suffix}`
}
