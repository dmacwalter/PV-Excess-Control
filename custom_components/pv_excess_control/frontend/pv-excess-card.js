/**
 * PV Excess Control - Lovelace Card
 *
 * A custom Lovelace card for the PV Excess Control integration.
 * Provides a power flow visualization, appliance controls, timeline,
 * forecast, and savings summary.
 *
 * Lit (LitElement, html, css) is bundled inline (~15KB) to avoid
 * CORS issues with external imports and to not depend on HA's
 * internal Lit version (per HA developer docs recommendation).
 */

// --- Bundled Lit 3.3.2 / LitElement 4.2.2 ---
(()=>{var M=globalThis,N=M.ShadowRoot&&(M.ShadyCSS===void 0||M.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,L=Symbol(),G=new WeakMap,b=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==L)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(N&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=G.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&G.set(e,t))}return t}toString(){return this.cssText}},Q=r=>new b(typeof r=="string"?r:r+"",void 0,L),k=(r,...t)=>{let e=r.length===1?r[0]:t.reduce((s,i,o)=>s+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+r[o+1],r[0]);return new b(e,r,L)},X=(r,t)=>{if(N)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=M.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,r.appendChild(s)}},D=N?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return Q(e)})(r):r;var{is:_t,defineProperty:ft,getOwnPropertyDescriptor:mt,getOwnPropertyNames:At,getOwnPropertySymbols:gt,getPrototypeOf:yt}=Object,T=globalThis,Y=T.trustedTypes,vt=Y?Y.emptyScript:"",St=T.reactiveElementPolyfillSupport,C=(r,t)=>r,j={toAttribute(r,t){switch(t){case Boolean:r=r?vt:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},et=(r,t)=>!_t(r,t),tt={attribute:!0,type:String,converter:j,reflect:!1,useDefault:!1,hasChanged:et};Symbol.metadata??=Symbol("metadata"),T.litPropertyMetadata??=new WeakMap;var $=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=tt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&ft(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:o}=mt(this.prototype,t)??{get(){return this[e]},set(n){this[e]=n}};return{get:i,set(n){let l=i?.call(this);o?.call(this,n),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??tt}static _$Ei(){if(this.hasOwnProperty(C("elementProperties")))return;let t=yt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(C("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(C("properties"))){let e=this.properties,s=[...At(e),...gt(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(D(i))}else t!==void 0&&e.push(D(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return X(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let o=(s.converter?.toAttribute!==void 0?s.converter:j).toAttribute(e,s.type);this._$Em=t,o==null?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let o=s.getPropertyOptions(i),n=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:j;this._$Em=i;let l=n.fromAttribute(e,o.type);this[i]=l??this._$Ej?.get(i)??l,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){if(t!==void 0){let n=this.constructor;if(i===!1&&(o=this[t]),s??=n.getPropertyOptions(t),!((s.hasChanged??et)(o,e)||s.useDefault&&s.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},n){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,n??e??this[t]),o!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,o]of this._$Ep)this[i]=o;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,o]of s){let{wrapped:n}=o,l=this[i];n!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,o,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[C("elementProperties")]=new Map,$[C("finalized")]=new Map,St?.({ReactiveElement:$}),(T.reactiveElementVersions??=[]).push("2.1.2");var K=globalThis,st=r=>r,R=K.trustedTypes,it=R?R.createPolicy("lit-html",{createHTML:r=>r}):void 0,lt="$lit$",f=`lit$${Math.random().toFixed(9).slice(2)}$`,ct="?"+f,Et=`<${ct}>`,y=document,x=()=>y.createComment(""),P=r=>r===null||typeof r!="object"&&typeof r!="function",F=Array.isArray,bt=r=>F(r)||typeof r?.[Symbol.iterator]=="function",B=`[ 	
\f\r]`,w=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,rt=/-->/g,ot=/>/g,A=RegExp(`>|${B}(?:([^\\s"'>=/]+)(${B}*=${B}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),nt=/'/g,ht=/"/g,pt=/^(?:script|style|textarea|title)$/i,J=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),dt=J(1),Mt=J(2),Nt=J(3),v=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),at=new WeakMap,g=y.createTreeWalker(y,129);function ut(r,t){if(!F(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return it!==void 0?it.createHTML(t):t}var Ct=(r,t)=>{let e=r.length-1,s=[],i,o=t===2?"<svg>":t===3?"<math>":"",n=w;for(let l=0;l<e;l++){let h=r[l],c,d,a=-1,u=0;for(;u<h.length&&(n.lastIndex=u,d=n.exec(h),d!==null);)u=n.lastIndex,n===w?d[1]==="!--"?n=rt:d[1]!==void 0?n=ot:d[2]!==void 0?(pt.test(d[2])&&(i=RegExp("</"+d[2],"g")),n=A):d[3]!==void 0&&(n=A):n===A?d[0]===">"?(n=i??w,a=-1):d[1]===void 0?a=-2:(a=n.lastIndex-d[2].length,c=d[1],n=d[3]===void 0?A:d[3]==='"'?ht:nt):n===ht||n===nt?n=A:n===rt||n===ot?n=w:(n=A,i=void 0);let _=n===A&&r[l+1].startsWith("/>")?" ":"";o+=n===w?h+Et:a>=0?(s.push(c),h.slice(0,a)+lt+h.slice(a)+f+_):h+f+(a===-2?l:_)}return[ut(r,o+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},U=class r{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,n=0,l=t.length-1,h=this.parts,[c,d]=Ct(t,e);if(this.el=r.createElement(c,s),g.currentNode=this.el.content,e===2||e===3){let a=this.el.content.firstChild;a.replaceWith(...a.childNodes)}for(;(i=g.nextNode())!==null&&h.length<l;){if(i.nodeType===1){if(i.hasAttributes())for(let a of i.getAttributeNames())if(a.endsWith(lt)){let u=d[n++],_=i.getAttribute(a).split(f),H=/([.?@])?(.*)/.exec(u);h.push({type:1,index:o,name:H[2],strings:_,ctor:H[1]==="."?I:H[1]==="?"?V:H[1]==="@"?W:E}),i.removeAttribute(a)}else a.startsWith(f)&&(h.push({type:6,index:o}),i.removeAttribute(a));if(pt.test(i.tagName)){let a=i.textContent.split(f),u=a.length-1;if(u>0){i.textContent=R?R.emptyScript:"";for(let _=0;_<u;_++)i.append(a[_],x()),g.nextNode(),h.push({type:2,index:++o});i.append(a[u],x())}}}else if(i.nodeType===8)if(i.data===ct)h.push({type:2,index:o});else{let a=-1;for(;(a=i.data.indexOf(f,a+1))!==-1;)h.push({type:7,index:o}),a+=f.length-1}o++}}static createElement(t,e){let s=y.createElement("template");return s.innerHTML=t,s}};function S(r,t,e=r,s){if(t===v)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,o=P(t)?void 0:t._$litDirective$;return i?.constructor!==o&&(i?._$AO?.(!1),o===void 0?i=void 0:(i=new o(r),i._$AT(r,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=S(r,i._$AS(r,t.values),i,s)),t}var z=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??y).importNode(e,!0);g.currentNode=i;let o=g.nextNode(),n=0,l=0,h=s[0];for(;h!==void 0;){if(n===h.index){let c;h.type===2?c=new O(o,o.nextSibling,this,t):h.type===1?c=new h.ctor(o,h.name,h.strings,this,t):h.type===6&&(c=new q(o,this,t)),this._$AV.push(c),h=s[++l]}n!==h?.index&&(o=g.nextNode(),n++)}return g.currentNode=y,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},O=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=S(this,t,e),P(t)?t===p||t==null||t===""?(this._$AH!==p&&this._$AR(),this._$AH=p):t!==this._$AH&&t!==v&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):bt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==p&&P(this._$AH)?this._$AA.nextSibling.data=t:this.T(y.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=U.createElement(ut(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let o=new z(i,this),n=o.u(this.options);o.p(e),this.T(n),this._$AH=o}}_$AC(t){let e=at.get(t.strings);return e===void 0&&at.set(t.strings,e=new U(t)),e}k(t){F(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let o of t)i===e.length?e.push(s=new r(this.O(x()),this.O(x()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=st(t).nextSibling;st(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},E=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=p,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=p}_$AI(t,e=this,s,i){let o=this.strings,n=!1;if(o===void 0)t=S(this,t,e,0),n=!P(t)||t!==this._$AH&&t!==v,n&&(this._$AH=t);else{let l=t,h,c;for(t=o[0],h=0;h<o.length-1;h++)c=S(this,l[s+h],e,h),c===v&&(c=this._$AH[h]),n||=!P(c)||c!==this._$AH[h],c===p?t=p:t!==p&&(t+=(c??"")+o[h+1]),this._$AH[h]=c}n&&!i&&this.j(t)}j(t){t===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},I=class extends E{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===p?void 0:t}},V=class extends E{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==p)}},W=class extends E{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=S(this,t,e,0)??p)===v)return;let s=this._$AH,i=t===p&&s!==p||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==p&&(s===p||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},q=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){S(this,t)}};var wt=K.litHtmlPolyfillSupport;wt?.(U,O),(K.litHtmlVersions??=[]).push("3.3.2");var $t=(r,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let o=e?.renderBefore??null;s._$litPart$=i=new O(t.insertBefore(x(),o),o,void 0,e??{})}return i._$AI(r),i};var Z=globalThis,m=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=$t(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return v}};m._$litElement$=!0,m.finalized=!0,Z.litElementHydrateSupport?.({LitElement:m});var xt=Z.litElementPolyfillSupport;xt?.({LitElement:m});(Z.litElementVersions??=[]).push("4.2.2");window.__pv_lit={LitElement:m,html:dt,css:k};})();
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/


// --- Extract Lit from bundle ---
const { LitElement, html, css } = window.__pv_lit;
delete window.__pv_lit; // Clean up global


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format watts into a human-readable string with appropriate units.
 * Values >= 1000 W are shown in kW.
 */
function formatPower(watts) {
  if (watts == null || isNaN(watts)) return "-- W";
  const abs = Math.abs(watts);
  if (abs >= 1000) {
    return `${(watts / 1000).toFixed(1)} kW`;
  }
  return `${Math.round(watts)} W`;
}

/**
 * Format a percentage value.
 */
function formatPercent(value) {
  if (value == null || isNaN(value)) return "--%";
  return `${Math.round(value)}%`;
}

// ---------------------------------------------------------------------------
// Card element
// ---------------------------------------------------------------------------

class PvExcessCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _entities: { type: Object },
    };
  }

  // -- Configuration --------------------------------------------------------

  setConfig(config) {
    if (!config) {
      throw new Error("No configuration provided");
    }
    this.config = {
      show_power_flow: true,
      show_appliances: true,
      show_timeline: true,
      show_forecast: true,
      show_savings: true,
      compact: false,
      ...config,
    };
  }

  // -- HA entity wiring -----------------------------------------------------

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;
    this._updateEntities();
    // Trigger Lit re-render
    this.requestUpdate("hass", oldHass);
  }

  get hass() {
    return this._hass;
  }

  /**
   * Discover entities belonging to the pv_excess_control domain.
   * Groups them by platform type for easy access by the render methods.
   */
  _updateEntities() {
    if (!this._hass) return;

    const all = Object.keys(this._hass.states);
    const prefix = "pv_excess_control";

    // Rebuild entity buckets on every hass update so state values stay fresh.
    // (A previous optimization skipped the rebuild when entity IDs hadn't
    // changed, but that left stale state-object references in the buckets,
    // causing the appliance/forecast/savings sections to show outdated values.)
    const sensors = {};
    const switches = {};
    const binarySensors = {};
    const numbers = {};
    const selects = {};

    for (const eid of all) {
      const state = this._hass.states[eid];
      if (!state) continue;

      // Match entities whose entity_id contains the integration domain
      // e.g. sensor.pv_excess_control_excess_power
      const objId = eid.split(".")[1] || "";
      if (!objId.startsWith(prefix)) continue;

      if (eid.startsWith("sensor.")) sensors[eid] = state;
      else if (eid.startsWith("switch.")) switches[eid] = state;
      else if (eid.startsWith("binary_sensor.")) binarySensors[eid] = state;
      else if (eid.startsWith("number.")) numbers[eid] = state;
      else if (eid.startsWith("select.")) selects[eid] = state;
    }

    this._entities = { sensors, switches, binarySensors, numbers, selects };
  }

  // -- Rendering ------------------------------------------------------------

  render() {
    if (!this._hass) return html``;

    return html`
      <ha-card>
        ${this.config.show_power_flow ? this._renderPowerFlow() : ""}
        ${this.config.show_appliances ? this._renderAppliances() : ""}
        ${!this.config.compact && this.config.show_timeline
          ? this._renderTimeline()
          : ""}
        ${!this.config.compact && this.config.show_forecast
          ? this._renderForecast()
          : ""}
        ${this.config.show_savings ? this._renderSavings() : ""}
      </ha-card>
    `;
  }

  // -- Power Flow Section ---------------------------------------------------

  /**
   * Read a specific sensor's numeric value by a suffix match against the
   * entity object_id.  E.g. suffix "excess_power" matches
   * "sensor.pv_excess_control_excess_power".
   */
  _sensorValue(suffix) {
    if (!this._entities || !this._entities.sensors) return null;
    for (const [eid, state] of Object.entries(this._entities.sensors)) {
      if (eid.endsWith(suffix)) {
        const val = parseFloat(state.state);
        return isNaN(val) ? null : val;
      }
    }
    return null;
  }

  /**
   * Get the attributes of the excess_power sensor (contains source entity IDs).
   */
  _getExcessPowerAttrs() {
    if (!this._entities || !this._entities.sensors) return {};
    for (const [eid, state] of Object.entries(this._entities.sensors)) {
      if (eid.endsWith("excess_power")) {
        return state.attributes || {};
      }
    }
    return {};
  }

  /**
   * Read the integration's power state attributes from the coordinator
   * data exposed via sensor attributes.
   */
  _getPowerData() {
    // Read power flow values directly from the user's original sensors
    // (no data duplication). The excess_power sensor exposes source entity
    // IDs as attributes (source_pv_power, source_grid_export, etc.).
    const sensors = this._entities ? this._entities.sensors : {};
    let sourceAttrs = {};

    for (const [eid, state] of Object.entries(sensors)) {
      if (eid.endsWith("excess_power")) {
        sourceAttrs = state.attributes || {};
        break;
      }
    }

    // Read a value from an original source sensor by its entity_id
    const readSource = (entityId) => {
      if (!entityId || !this._hass) return null;
      const state = this._hass.states[entityId];
      if (!state || state.state === "unavailable" || state.state === "unknown") return null;
      const val = parseFloat(state.state);
      return isNaN(val) ? null : val;
    };

    // For combined import/export sensor: positive=export, negative=import
    let gridExport = readSource(sourceAttrs.source_grid_export);
    let gridImport = null;
    const importExportVal = readSource(sourceAttrs.source_import_export);
    if (importExportVal != null && gridExport == null) {
      gridExport = Math.max(0, importExportVal);
      gridImport = Math.abs(Math.min(0, importExportVal));
    }

    // Battery power: combined or separate charge/discharge
    let batteryPower = readSource(sourceAttrs.source_battery_power);
    if (batteryPower == null) {
      const charge = readSource(sourceAttrs.source_battery_charge_power);
      const discharge = readSource(sourceAttrs.source_battery_discharge_power);
      if (charge != null || discharge != null) {
        batteryPower = (charge || 0) - (discharge || 0);
      }
    }

    return {
      pvProduction: readSource(sourceAttrs.source_pv_power),
      gridExport: gridExport,
      gridImport: gridImport,
      loadPower: readSource(sourceAttrs.source_load_power),
      excessPower: this._sensorValue("excess_power"),
      batterySoc: readSource(sourceAttrs.source_battery_soc),
      batteryPower: batteryPower,
      currentPrice: readSource(sourceAttrs.source_price_sensor),
    };
  }

  _renderPowerFlow() {
    const d = this._getPowerData();

    // Determine battery state
    const batteryCharging =
      d.batteryPower != null && d.batteryPower > 0;
    const batteryDischarging =
      d.batteryPower != null && d.batteryPower < 0;
    const batteryAbsPower =
      d.batteryPower != null ? Math.abs(d.batteryPower) : 0;

    // Grid direction
    const gridExporting = (d.gridExport || 0) > (d.gridImport || 0);
    const gridPower = gridExporting
      ? d.gridExport || 0
      : d.gridImport || 0;

    // Flow line animation durations (faster = more power)
    const pvAnimDur = this._animDuration(d.pvProduction);
    const battAnimDur = this._animDuration(batteryAbsPower);
    const gridAnimDur = this._animDuration(gridPower);
    const homeAnimDur = this._animDuration(d.loadPower);

    // Tariff display
    const tariffStr =
      d.currentPrice != null ? `${d.currentPrice.toFixed(2)}/kWh` : null;

    return html`
      <div class="section power-flow">
        <svg
          viewBox="0 0 300 200"
          xmlns="http://www.w3.org/2000/svg"
          class="flow-svg"
        >
          <!-- PV (top center) -->
          <g class="pv-node" transform="translate(150,28)">
            <circle r="24" class="node-circle node-pv" />
            <text class="node-icon" dy="1" text-anchor="middle">&#9728;</text>
          </g>
          <text x="150" y="68" class="node-label" text-anchor="middle">
            PV: ${formatPower(d.pvProduction)}
          </text>

          <!-- Battery (bottom-left) -->
          <g class="battery-node" transform="translate(50,148)">
            <circle
              r="24"
              class="node-circle ${batteryCharging
                ? "node-battery-charge"
                : batteryDischarging
                ? "node-battery-discharge"
                : "node-battery"}"
            />
            <text class="node-icon" dy="1" text-anchor="middle">&#128267;</text>
          </g>
          <text x="50" y="188" class="node-label" text-anchor="middle">
            ${d.batterySoc != null ? formatPercent(d.batterySoc) : "N/A"}
          </text>
          ${d.batteryPower != null
            ? html`
                <text x="50" y="200" class="node-sub" text-anchor="middle">
                  ${batteryCharging ? "+" : batteryDischarging ? "-" : ""}${formatPower(batteryAbsPower)}
                </text>
              `
            : ""}

          <!-- Home (bottom-center) -->
          <g class="home-node" transform="translate(150,148)">
            <circle r="24" class="node-circle node-home" />
            <text class="node-icon" dy="2" text-anchor="middle">&#127968;</text>
          </g>
          <text x="150" y="188" class="node-label" text-anchor="middle">
            ${formatPower(d.loadPower)}
          </text>

          <!-- Grid (bottom-right) -->
          <g class="grid-node" transform="translate(250,148)">
            <circle
              r="24"
              class="node-circle ${gridExporting
                ? "node-grid-export"
                : "node-grid-import"}"
            />
            <text class="node-icon" dy="2" text-anchor="middle">&#9889;</text>
          </g>
          <text x="250" y="188" class="node-label" text-anchor="middle">
            ${gridExporting ? "" : ""}${formatPower(gridPower)}
          </text>
          <text x="250" y="200" class="node-sub" text-anchor="middle">
            ${gridExporting ? "exporting" : gridPower > 0 ? "importing" : ""}
          </text>

          <!-- Flow lines: PV -> Battery -->
          ${d.pvProduction != null && d.pvProduction > 0 && batteryCharging
            ? html`
                <line
                  x1="150" y1="52" x2="50" y2="124"
                  class="flow-line flow-battery-charge"
                  style="animation-duration: ${battAnimDur}s"
                />
              `
            : ""}

          <!-- Flow lines: PV -> Home -->
          ${d.pvProduction != null && d.pvProduction > 0
            ? html`
                <line
                  x1="150" y1="52" x2="150" y2="124"
                  class="flow-line flow-solar"
                  style="animation-duration: ${pvAnimDur}s"
                />
              `
            : ""}

          <!-- Flow lines: PV -> Grid (export) -->
          ${d.pvProduction != null && d.pvProduction > 0 && gridExporting
            ? html`
                <line
                  x1="150" y1="52" x2="250" y2="124"
                  class="flow-line flow-grid-export"
                  style="animation-duration: ${gridAnimDur}s"
                />
              `
            : ""}

          <!-- Flow lines: Battery -> Home (discharging) -->
          ${batteryDischarging
            ? html`
                <line
                  x1="74" y1="148" x2="126" y2="148"
                  class="flow-line flow-battery-discharge"
                  style="animation-duration: ${battAnimDur}s"
                />
              `
            : ""}

          <!-- Flow lines: Grid -> Home (importing) -->
          ${!gridExporting && gridPower > 0
            ? html`
                <line
                  x1="226" y1="148" x2="174" y2="148"
                  class="flow-line flow-grid-import"
                  style="animation-duration: ${gridAnimDur}s"
                />
              `
            : ""}
        </svg>

        <!-- Status bar -->
        <div class="power-status">
          <span class="status-item excess">
            Excess: ${formatPower(d.excessPower)}
          </span>
          ${tariffStr != null
            ? html`
                <span class="status-divider">|</span>
                <span class="status-item tariff">Tariff: ${tariffStr}</span>
              `
            : ""}
        </div>
      </div>
    `;
  }

  /**
   * Calculate animation duration inversely proportional to power.
   * More power = faster animation (shorter duration).
   * Returns a value in seconds, clamped between 1 and 6.
   */
  _animDuration(watts) {
    if (!watts || watts <= 0) return 6;
    // 5000 W -> ~1s, 100 W -> ~5s
    const dur = 6 - (Math.min(watts, 5000) / 5000) * 5;
    return Math.max(1, dur);
  }

  // -- Appliance Section ----------------------------------------------------

  /**
   * Scan all discovered entities to build an array of appliance data objects.
   *
   * IMPORTANT: This discovery relies on entity ID naming conventions.
   * Entity IDs follow the pattern produced by HA's has_entity_name + slugified
   * appliance name, e.g.:
   *   sensor.pv_excess_control_{slug}_power
   *   sensor.pv_excess_control_{slug}_runtime_today
   *   sensor.pv_excess_control_{slug}_energy_today
   *   sensor.pv_excess_control_{slug}_status
   *   switch.pv_excess_control_{slug}_override
   *   switch.pv_excess_control_{slug}_enabled
   *   binary_sensor.pv_excess_control_{slug}_active
   *   number.pv_excess_control_{slug}_priority
   *
   * We extract the slug by stripping the known prefix and each known suffix,
   * then group all matching entity IDs by slug.
   *
   * NOTE: If users manually rename entity IDs (breaking the pv_excess_control_
   * prefix convention), appliances will not be discovered by the card.
   * A future improvement could read appliance data via coordinator websocket
   * subscription instead of entity ID pattern matching.
   */
  _getApplianceData() {
    if (!this._entities) return [];

    const { sensors, switches, binarySensors, numbers } = this._entities;

    // Suffixes that indicate per-appliance sensor entities
    const SENSOR_SUFFIXES = ["_power", "_runtime_today", "_energy_today", "_status"];
    const SWITCH_SUFFIXES = ["_override", "_enabled"];
    const BINARY_SUFFIXES = ["_active"];
    const NUMBER_SUFFIXES = ["_priority"];

    const SENSOR_PREFIX = "sensor.pv_excess_control_";
    const SWITCH_PREFIX = "switch.pv_excess_control_";
    const BINARY_PREFIX = "binary_sensor.pv_excess_control_";
    const NUMBER_PREFIX = "number.pv_excess_control_";

    // Collect all unique appliance slugs
    const slugSet = new Set();

    const extractSlug = (eid, prefix, suffixes) => {
      if (!eid.startsWith(prefix)) return null;
      const objId = eid.slice(prefix.length);
      for (const suf of suffixes) {
        if (objId.endsWith(suf)) {
          return objId.slice(0, objId.length - suf.length);
        }
      }
      return null;
    };

    for (const eid of Object.keys(sensors || {})) {
      const slug = extractSlug(eid, SENSOR_PREFIX, SENSOR_SUFFIXES);
      // Skip system-level sensors that have no appliance slug or whose slug
      // maps to known system sensors.
      if (slug && slug !== "excess" && slug !== "plan_confidence" && slug !== "") {
        slugSet.add(slug);
      }
    }
    for (const eid of Object.keys(switches || {})) {
      const slug = extractSlug(eid, SWITCH_PREFIX, SWITCH_SUFFIXES);
      if (slug && slug !== "control" && slug !== "force_charge" && slug !== "") {
        slugSet.add(slug);
      }
    }
    for (const eid of Object.keys(binarySensors || {})) {
      const slug = extractSlug(eid, BINARY_PREFIX, BINARY_SUFFIXES);
      if (slug && slug !== "excess" && slug !== "") {
        slugSet.add(slug);
      }
    }
    for (const eid of Object.keys(numbers || {})) {
      const slug = extractSlug(eid, NUMBER_PREFIX, NUMBER_SUFFIXES);
      if (slug && slug !== "") slugSet.add(slug);
    }

    if (slugSet.size === 0) return [];

    // Build appliance data objects from the discovered slugs
    const appliances = [];

    for (const slug of slugSet) {
      // Resolve each entity by constructing the expected entity ID
      const powerEid      = `${SENSOR_PREFIX}${slug}_power`;
      const runtimeEid    = `${SENSOR_PREFIX}${slug}_runtime_today`;
      const energyEid     = `${SENSOR_PREFIX}${slug}_energy_today`;
      const statusEid     = `${SENSOR_PREFIX}${slug}_status`;
      const overrideEid   = `${SWITCH_PREFIX}${slug}_override`;
      const enabledEid    = `${SWITCH_PREFIX}${slug}_enabled`;
      const activeEid     = `${BINARY_PREFIX}${slug}_active`;
      const priorityEid   = `${NUMBER_PREFIX}${slug}_priority`;

      const powerState    = (sensors || {})[powerEid];
      const runtimeState  = (sensors || {})[runtimeEid];
      const energyState   = (sensors || {})[energyEid];
      const statusState   = (sensors || {})[statusEid];
      const overrideState = (switches || {})[overrideEid];
      const enabledState  = (switches || {})[enabledEid];
      const activeState   = (binarySensors || {})[activeEid];
      const priorityState = (numbers || {})[priorityEid];

      // Derive a human-readable name from the slug (replace underscores, title-case)
      const friendlyName = slug
        .split("_")
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");

      const power     = powerState    ? parseFloat(powerState.state)    : null;
      const runtime   = runtimeState  ? parseFloat(runtimeState.state)  : null;
      const energy    = energyState   ? parseFloat(energyState.state)   : null;
      const priority  = priorityState ? parseFloat(priorityState.state) : 999;

      const active = activeState
        ? activeState.state === "on"
        : (!isNaN(power) && power > 0);

      const override = overrideState ? overrideState.state === "on" : false;
      const enabled  = enabledState  ? enabledState.state  === "on" : true;

      const statusReason = statusState ? statusState.state : null;

      appliances.push({
        slug,
        name:           friendlyName,
        priority:       isNaN(priority) ? 999 : priority,
        active,
        override,
        enabled,
        power:          isNaN(power)   ? null : power,
        runtime:        isNaN(runtime) ? null : runtime,
        energy:         isNaN(energy)  ? null : energy,
        statusReason:   statusReason === "unknown" || statusReason === "unavailable"
                          ? null
                          : statusReason,
        overrideEntity: overrideEid,
      });
    }

    return appliances;
  }

  _renderAppliances() {
    const appliances = this._getApplianceData();

    if (!appliances.length) {
      return html`
        <div class="section appliances">
          <div class="section-title">Appliances</div>
          <div class="empty">No appliances configured</div>
        </div>
      `;
    }

    return html`
      <div class="section appliances">
        <div class="section-title">Appliances</div>
        ${appliances
          .sort((a, b) => a.priority - b.priority)
          .map(
            (app, idx) => html`
              <div class="appliance ${app.active ? "active" : "idle"}">
                <div class="appliance-row">
                  <span class="priority">#${app.priority < 999 ? app.priority : idx + 1}</span>
                  <span class="status-dot ${app.active ? "on" : "off"}"></span>
                  <span class="name">${app.name}</span>
                  <span class="power">
                    ${app.active ? formatPower(app.power) : "— idle"}
                  </span>
                  <button
                    class="override-btn ${app.override ? "active" : ""}"
                    title="${app.override ? "Override ON – click to cancel" : "Manual override"}"
                    @click=${() => this._toggleOverride(app.overrideEntity)}
                  >
                    ↻
                  </button>
                </div>
                <div class="appliance-detail">
                  ${app.statusReason ? app.statusReason : ""}${app.runtime != null
                    ? ` · ${app.runtime.toFixed(1)}h today`
                    : ""}${app.energy != null
                    ? ` · ${app.energy.toFixed(2)} kWh`
                    : ""}
                </div>
              </div>
            `
          )}
      </div>
    `;
  }

  /**
   * Toggle a manual override switch via the HA switch service.
   */
  _toggleOverride(entityId) {
    if (!entityId || !this._hass) return;
    const state = this._hass.states[entityId];
    if (!state) return;
    this._hass.callService(
      "switch",
      state.state === "on" ? "turn_off" : "turn_on",
      { entity_id: entityId }
    );
  }

  // -- Helper: read a named entity state value by suffix --------------------

  /**
   * Returns the raw state string of the first entity whose entity_id ends
   * with the given suffix in the given platform bucket.
   * platform: 'sensor' | 'switch' | 'binarySensor' | 'number' | 'select'
   * suffix example: 'solar_forecast_remaining'
   */
  _getEntityState(platform, suffix) {
    if (!this._entities) return null;
    // Map platform name to the bucket key used in _entities
    const bucketKey = platform === 'binarySensor' ? 'binarySensors'
                    : platform === 'sensor'        ? 'sensors'
                    : platform === 'switch'        ? 'switches'
                    : platform === 'number'        ? 'numbers'
                    : platform === 'select'        ? 'selects'
                    : platform + 's';
    const bucket = this._entities[bucketKey] || {};
    for (const [eid, state] of Object.entries(bucket)) {
      if (eid.endsWith(suffix)) {
        const s = state.state;
        return s === 'unavailable' || s === 'unknown' ? null : s;
      }
    }
    return null;
  }

  // -- Timeline section ------------------------------------------------------

  _renderTimeline() {
    const appliances = this._getApplianceData();
    const now = new Date();
    const startHour = 6;
    const endHour = 22;
    const totalHours = endHour - startHour;
    const currentHour = now.getHours() + now.getMinutes() / 60;
    const nowPct = Math.max(0, Math.min(100,
      ((currentHour - startHour) / totalHours) * 100));

    // SVG coordinate helpers
    // x range: 44 (label area) to 394; 350px usable track width
    const SVG_LEFT = 44;
    const SVG_RIGHT = 394;
    const SVG_TRACK_W = SVG_RIGHT - SVG_LEFT;
    const rowCount = Math.max(appliances.length, 1);
    const svgH = 28 + rowCount * 26;
    const nowX = SVG_LEFT + (nowPct / 100) * SVG_TRACK_W;

    // Hour tick marks (6 to 22)
    const hourTicks = Array.from({ length: totalHours + 1 }, (_, i) => {
      const x = SVG_LEFT + (i / totalHours) * SVG_TRACK_W;
      const hour = startHour + i;
      return html`
        <line x1="${x}" y1="20" x2="${x}" y2="${svgH}"
              stroke="var(--divider-color,#e0e0e0)" stroke-width="0.5"/>
        <text x="${x}" y="13" text-anchor="middle" font-size="9"
              fill="var(--secondary-text-color,#727272)">${hour}</text>
      `;
    });

    // Per-appliance rows
    const appRows = appliances.length > 0
      ? appliances.map((app, i) => {
          const y = 28 + i * 26;
          return html`
            <text x="${SVG_LEFT - 4}" y="${y + 14}" text-anchor="end"
                  font-size="9" fill="var(--primary-text-color,#212121)">
              ${app.name.substring(0, 7)}
            </text>
            <!-- Background track -->
            <rect x="${SVG_LEFT}" y="${y + 6}" width="${SVG_TRACK_W}" height="12"
                  rx="2" fill="var(--divider-color,#e0e0e0)" opacity="0.4"/>
            ${app.active ? html`
              <!-- Running-now indicator from nowX to end of track -->
              <rect x="${nowX}" y="${y + 6}"
                    width="${SVG_RIGHT - nowX}" height="12"
                    rx="2" fill="var(--success-color,#4caf50)" opacity="0.6"/>
              <!-- Circle dot at current-time edge -->
              <circle cx="${nowX}" cy="${y + 12}" r="5"
                      fill="var(--success-color,#4caf50)"/>
            ` : ''}
          `;
        })
      : html`
          <text x="${SVG_LEFT + SVG_TRACK_W / 2}" y="${28 + 13}"
                text-anchor="middle" font-size="10"
                fill="var(--secondary-text-color,#727272)">
            No appliances found
          </text>
        `;

    return html`
      <div class="section timeline">
        <div class="section-title">Timeline (today)</div>
        <svg viewBox="0 0 400 ${svgH}" class="timeline-svg"
             xmlns="http://www.w3.org/2000/svg">
          <!-- Hour grid lines and labels -->
          ${hourTicks}
          <!-- "Now" vertical line -->
          <line x1="${nowX}" y1="17" x2="${nowX}" y2="${svgH}"
                stroke="var(--error-color,#f44336)" stroke-width="1.5"
                stroke-dasharray="3 2"/>
          <!-- Appliance rows -->
          ${appRows}
        </svg>
        <div class="timeline-legend">
          <span class="legend-item">
            <span class="legend-box legend-solar"></span>Solar powered
          </span>
          <!-- TODO: Cheap tariff and Planned visual segments not yet implemented -->
        </div>
      </div>
    `;
  }

  // -- Forecast & Plan section -----------------------------------------------

  _renderForecast() {
    // Read forecast from the configured source sensor (e.g. Solcast)
    let forecastRemaining = this._getEntityState('sensor', 'solar_forecast_remaining');
    if (forecastRemaining == null) {
      // Fallback: read directly from the source forecast sensor
      const sourceAttrs = this._getExcessPowerAttrs();
      const forecastEntity = sourceAttrs.source_forecast_sensor;
      if (forecastEntity && this._hass && this._hass.states[forecastEntity]) {
        const st = this._hass.states[forecastEntity];
        if (st.state !== "unavailable" && st.state !== "unknown") {
          forecastRemaining = st.state;
        }
      }
    }
    const planConfidence    = this._getEntityState('sensor', 'plan_confidence');
    const nextCheap         = this._getEntityState('sensor', 'next_cheap_window');
    const batteryTarget     = this._getEntityState('sensor', 'battery_target');

    const forecastNum = forecastRemaining != null ? parseFloat(forecastRemaining) : null;
    const confidenceNum = planConfidence != null ? parseFloat(planConfidence) : null;
    const allNull = (forecastNum == null || isNaN(forecastNum))
                    && (confidenceNum == null || isNaN(confidenceNum))
                    && nextCheap == null && batteryTarget == null;

    return html`
      <div class="section forecast">
        <div class="section-title">Forecast &amp; Plan</div>

        <div class="forecast-item">
          <span class="label">Solar remaining today</span>
          <span class="value">
            ${forecastNum != null && !isNaN(forecastNum)
              ? `${forecastNum.toFixed(1)} kWh`
              : 'N/A'}
          </span>
        </div>

        ${!isNaN(confidenceNum) && confidenceNum != null ? html`
          <div class="forecast-item forecast-confidence">
            <span class="label">Plan confidence</span>
            <div class="confidence-bar">
              <div class="confidence-fill"
                   style="width: ${Math.min(100, Math.round(confidenceNum))}%">
              </div>
            </div>
            <span class="value">${Math.round(confidenceNum)}%</span>
          </div>
        ` : ''}

        ${nextCheap != null ? html`
          <div class="forecast-item">
            <span class="label">Next cheap window</span>
            <span class="value">${nextCheap}</span>
          </div>
        ` : ''}

        ${batteryTarget != null ? html`
          <div class="forecast-item">
            <span class="label">Battery target</span>
            <span class="value">${batteryTarget}</span>
          </div>
        ` : ''}

        ${allNull ? html`
          <div class="forecast-empty">
            No forecast data available yet.
          </div>
        ` : ''}
      </div>
    `;
  }

  // -- Savings section -------------------------------------------------------

  _renderSavings() {
    const selfConsumption        = this._getEntityState('sensor', 'self_consumption_ratio');
    const savingsToday           = this._getEntityState('sensor', 'savings_today');
    const solarEnergy            = this._getEntityState('sensor', 'self_consumption_energy');
    const savingsMonth           = this._getEntityState('sensor', 'savings_month');
    const solarEnergyMonth       = this._getEntityState('sensor', 'solar_energy_month');
    const selfConsumptionMonthly = this._getEntityState('sensor', 'self_consumption_ratio_monthly');

    const fmtPercent = (v) => {
      if (v == null) return '—';
      const n = parseFloat(v);
      return isNaN(n) ? '—' : `${Math.round(n)}%`;
    };
    const fmtEuros = (v) => {
      if (v == null) return '—';
      const n = Number(v);
      return isNaN(n) ? '—' : `€${n.toFixed(2)}`;
    };
    const fmtKwh = (v) => {
      if (v == null) return '—';
      const n = Number(v);
      return isNaN(n) ? '—' : `${n.toFixed(1)} kWh`;
    };

    return html`
      <div class="section savings">
        <div class="section-title">Savings</div>
        <div class="savings-grid">
          <!-- Today column -->
          <div class="savings-col">
            <div class="savings-header">Today</div>
            <div class="savings-row">
              <span class="label">Self-use</span>
              <span class="value">${fmtPercent(selfConsumption)}</span>
            </div>
            <div class="savings-row">
              <span class="label">Saved</span>
              <span class="value">${fmtEuros(savingsToday)}</span>
            </div>
            <div class="savings-row">
              <span class="label">Solar</span>
              <span class="value">${fmtKwh(solarEnergy)}</span>
            </div>
          </div>

          <!-- Column divider -->
          <div class="savings-divider"></div>

          <!-- This month column -->
          <div class="savings-col">
            <div class="savings-header">This Month</div>
            <div class="savings-row">
              <span class="label">Self-use</span>
              <span class="value">${fmtPercent(selfConsumptionMonthly)}</span>
            </div>
            <div class="savings-row">
              <span class="label">Saved</span>
              <span class="value">${fmtEuros(savingsMonth)}</span>
            </div>
            <div class="savings-row">
              <span class="label">Solar</span>
              <span class="value">${fmtKwh(solarEnergyMonth)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // -- Styles ---------------------------------------------------------------

  static get styles() {
    return css`
      :host {
        display: block;
      }

      ha-card {
        padding: 16px;
        overflow: hidden;
      }

      /* --- Sections --- */

      .section {
        margin-bottom: 16px;
      }
      .section:last-child {
        margin-bottom: 0;
      }

      .section-title {
        font-weight: 500;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--secondary-text-color, #727272);
        margin-bottom: 8px;
      }

      .placeholder-text {
        color: var(--secondary-text-color, #727272);
        font-size: 13px;
        font-style: italic;
        padding: 8px 0;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }

      /* --- Power Flow --- */

      .power-flow {
        text-align: center;
      }

      .flow-svg {
        width: 100%;
        max-width: 400px;
        height: auto;
      }

      /* Node circles */
      .node-circle {
        fill: var(--card-background-color, #fff);
        stroke-width: 2.5;
      }
      .node-pv {
        stroke: #f9a825; /* amber */
        fill: rgba(249, 168, 37, 0.1);
      }
      .node-battery {
        stroke: #78909c; /* blue-grey */
        fill: rgba(120, 144, 156, 0.08);
      }
      .node-battery-charge {
        stroke: #43a047; /* green */
        fill: rgba(67, 160, 71, 0.1);
      }
      .node-battery-discharge {
        stroke: #ef6c00; /* orange */
        fill: rgba(239, 108, 0, 0.1);
      }
      .node-home {
        stroke: #1e88e5; /* blue */
        fill: rgba(30, 136, 229, 0.08);
      }
      .node-grid-export {
        stroke: #43a047; /* green */
        fill: rgba(67, 160, 71, 0.1);
      }
      .node-grid-import {
        stroke: #e53935; /* red */
        fill: rgba(229, 57, 53, 0.1);
      }

      /* Node text */
      .node-icon {
        font-size: 18px;
        dominant-baseline: central;
        pointer-events: none;
      }
      .node-label {
        font-size: 12px;
        font-weight: 500;
        fill: var(--primary-text-color, #212121);
      }
      .node-sub {
        font-size: 10px;
        fill: var(--secondary-text-color, #727272);
      }

      /* Animated flow lines */
      .flow-line {
        stroke-width: 2;
        stroke-dasharray: 6 4;
        fill: none;
        animation-name: dash-flow;
        animation-timing-function: linear;
        animation-iteration-count: infinite;
      }

      @keyframes dash-flow {
        to {
          stroke-dashoffset: -20;
        }
      }

      .flow-solar {
        stroke: #f9a825;
      }
      .flow-battery-charge {
        stroke: #43a047;
      }
      .flow-battery-discharge {
        stroke: #ef6c00;
      }
      .flow-grid-export {
        stroke: #43a047;
      }
      .flow-grid-import {
        stroke: #e53935;
      }

      /* Status bar */
      .power-status {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        padding: 8px 0 0;
        font-size: 14px;
        color: var(--primary-text-color, #212121);
      }

      .status-divider {
        color: var(--divider-color, #bdbdbd);
      }

      .status-item.excess {
        font-weight: 500;
      }
      .status-item.tariff {
        color: var(--secondary-text-color, #727272);
      }

      /* --- Appliance List --- */

      .appliances {
        border-top: 1px solid var(--divider-color, #e0e0e0);
        padding-top: 8px;
      }

      .appliance {
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .appliance:last-child {
        border-bottom: none;
      }

      .appliance-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .priority {
        color: var(--secondary-text-color, #727272);
        font-size: 0.85em;
        min-width: 24px;
      }

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .status-dot.on {
        background: var(--success-color, #4caf50);
      }
      .status-dot.off {
        background: var(--disabled-color, #bdbdbd);
      }

      .name {
        flex: 1;
        font-weight: 500;
      }

      .power {
        font-family: monospace;
        font-size: 0.9em;
      }

      .override-btn {
        background: none;
        border: 1px solid var(--divider-color, #bdbdbd);
        border-radius: 4px;
        cursor: pointer;
        padding: 2px 6px;
        font-size: 1em;
        line-height: 1.4;
        color: var(--primary-text-color, #212121);
        transition: background 0.15s, color 0.15s;
      }
      .override-btn:hover {
        background: var(--secondary-background-color, #f5f5f5);
      }
      .override-btn.active {
        background: var(--primary-color, #03a9f4);
        color: white;
        border-color: var(--primary-color, #03a9f4);
      }

      .appliance-detail {
        font-size: 0.85em;
        color: var(--secondary-text-color, #727272);
        padding-left: 40px;
        padding-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .empty {
        font-size: 13px;
        font-style: italic;
        color: var(--secondary-text-color, #727272);
        padding: 8px 0;
      }

      /* --- Timeline --- */

      .timeline {
        border-top: 1px solid var(--divider-color, #e0e0e0);
        padding-top: 8px;
      }

      .timeline-svg {
        width: 100%;
        height: auto;
        display: block;
      }

      .timeline-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        padding-top: 6px;
        font-size: 11px;
        color: var(--secondary-text-color, #727272);
      }

      .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .legend-box {
        display: inline-block;
        width: 12px;
        height: 8px;
        border-radius: 2px;
        flex-shrink: 0;
      }

      .legend-solar {
        background: var(--success-color, #4caf50);
        opacity: 0.75;
      }

      .legend-tariff {
        background: var(--info-color, #2196f3);
        opacity: 0.75;
      }

      .legend-planned {
        background: transparent;
        border: 1px dashed var(--secondary-text-color, #727272);
      }

      /* --- Forecast --- */

      .forecast {
        border-top: 1px solid var(--divider-color, #e0e0e0);
        padding-top: 8px;
      }

      .forecast-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 4px 0;
        font-size: 13px;
        color: var(--primary-text-color, #212121);
      }

      .forecast-item .label {
        flex: 1;
        color: var(--secondary-text-color, #727272);
      }

      .forecast-item .value {
        font-weight: 500;
        white-space: nowrap;
      }

      .forecast-confidence {
        flex-wrap: wrap;
      }

      .confidence-bar {
        flex: 1;
        height: 8px;
        background: var(--divider-color, #e0e0e0);
        border-radius: 4px;
        overflow: hidden;
        min-width: 60px;
      }

      .confidence-fill {
        height: 100%;
        background: var(--primary-color, #03a9f4);
        border-radius: 4px;
        transition: width 0.4s ease;
      }

      .forecast-empty {
        font-size: 13px;
        font-style: italic;
        color: var(--secondary-text-color, #727272);
        padding: 4px 0;
      }

      /* --- Savings --- */

      .savings {
        border-top: 1px solid var(--divider-color, #e0e0e0);
        padding-top: 8px;
      }

      .savings-grid {
        display: flex;
        gap: 0;
      }

      .savings-col {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .savings-divider {
        width: 1px;
        background: var(--divider-color, #e0e0e0);
        margin: 0 12px;
        align-self: stretch;
      }

      .savings-header {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        color: var(--secondary-text-color, #727272);
        margin-bottom: 4px;
      }

      .savings-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        padding: 2px 0;
        color: var(--primary-text-color, #212121);
      }

      .savings-row .label {
        color: var(--secondary-text-color, #727272);
      }

      .savings-row .value {
        font-weight: 500;
      }
    `;
  }

  // -- Card API -------------------------------------------------------------

  getCardSize() {
    return this.config && this.config.compact ? 3 : 8;
  }

  static getConfigElement() {
    return document.createElement("pv-excess-card-editor");
  }

  static getStubConfig() {
    return {
      show_power_flow: true,
      show_appliances: true,
      show_timeline: true,
      show_forecast: true,
      show_savings: true,
      compact: false,
    };
  }
}

if (!customElements.get("pv-excess-control-card")) {
  customElements.define("pv-excess-control-card", PvExcessCard);
}

// Register with HA's custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "pv-excess-control-card",
  name: "PV Excess Control",
  description: "Full-featured dashboard for PV Excess Control integration",
  preview: true,
});
