/** Only the explicit backend route manifest invokes this Pages Function. */
export async function onRequest({request,env}) {
  const source=new URL(request.url);
  if(!/^\/(api|ws|admin|health|static)(\/|$)/.test(source.pathname)) return new Response("Not found",{status:404});
  if(source.pathname.startsWith('/api/v1/research/tools'))return new Response("Not found",{status:404});
  if(!env.BACKEND_ORIGIN||!env.QUANTNEST_PROXY_TOKEN) return unavailable("origin_unconfigured");
  let target;
  try{target=new URL(env.BACKEND_ORIGIN);if(target.protocol!=="https:"||target.username||target.password||target.search||target.hash||target.pathname!=="/")return unavailable("invalid_origin")}catch{return unavailable("invalid_origin")}
  target.pathname=source.pathname;target.search=source.search;
  const headers=new Headers(request.headers);
  for(const key of ["X-QuantNest-Proxy-Token","X-QuantNest-Client-IP","X-Forwarded-Host","X-Forwarded-Proto","X-Forwarded-For","Forwarded"])headers.delete(key);
  headers.set("X-QuantNest-Proxy-Token",env.QUANTNEST_PROXY_TOKEN);
  headers.set("X-Forwarded-Host",source.host);headers.set("X-Forwarded-Proto","https");
  headers.set("X-Forwarded-For",request.headers.get("CF-Connecting-IP")||"");
  headers.set("X-QuantNest-Client-IP",request.headers.get("CF-Connecting-IP")||"");
  const upstream=new Request(target,{method:request.method,headers,body:["GET","HEAD"].includes(request.method)?undefined:request.body,redirect:"manual",duplex:"half"});
  try{
    const response=await fetch(upstream,{cf:{cacheTtl:0,cacheEverything:false}});
    if(response.status===101)return response;
    const outgoing=new Headers(response.headers);outgoing.set("Cache-Control","private, no-store");outgoing.set("CDN-Cache-Control","no-store");
    const location=outgoing.get("Location");if(location){const destination=new URL(location,target);if(destination.origin===target.origin){destination.host=source.host;outgoing.set("Location",destination.href)}}
    return new Response(response.body,{status:response.status,statusText:response.statusText,headers:outgoing});
  }catch{return unavailable("origin_unavailable")}
}
function unavailable(code){return Response.json({code,message:"The application backend is temporarily unavailable. Please retry."},{status:503,headers:{"Cache-Control":"no-store"}})}
