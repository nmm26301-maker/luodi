package cn.luodi.app;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.view.View;
import android.view.HapticFeedbackConstants;
import android.view.WindowManager;
import android.widget.Toast;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** Offline UI. Only packaged assets are served, using a dedicated HTTPS origin. */
public final class MainActivity extends Activity {
    private WebView web;
    private SharedPreferences prefs;
    private String pendingExport;
    private static final String ORIGIN="https://appassets.androidplatform.net";
    private static final int EXPORT=41, IMPORT=42;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        prefs=getSharedPreferences("luodi",MODE_PRIVATE);
        pendingExport=prefs.getString("pendingExport",null);
        getWindow().setStatusBarColor(Color.rgb(255,249,229));
        getWindow().setNavigationBarColor(Color.rgb(255,253,246));
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | (android.os.Build.VERSION.SDK_INT>=26?View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR:0));
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        web=new WebView(this);web.setBackgroundColor(Color.rgb(255,249,229));
        WebSettings s=web.getSettings();
        s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(false);s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);s.setAllowUniversalAccessFromFileURLs(false);s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setSupportZoom(false);s.setBuiltInZoomControls(false);s.setDisplayZoomControls(false);s.setTextZoom(100);
        web.setWebViewClient(new WebViewClient(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest r){return asset(r.getUrl());}
            @Override public WebResourceResponse shouldInterceptRequest(WebView v,String url){return asset(Uri.parse(url));}
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !isLocal(r.getUrl());}
            @Override public boolean shouldOverrideUrlLoading(WebView v,String url){return !isLocal(Uri.parse(url));}
        });
        web.addJavascriptInterface(new LocalBridge(),"LuodiNative");
        setContentView(web);web.loadUrl(ORIGIN+"/assets/index.html");
    }
    private boolean isLocal(Uri u){return "https".equals(u.getScheme())&&"appassets.androidplatform.net".equals(u.getHost())&&u.getPath()!=null&&u.getPath().startsWith("/assets/");}
    private WebResourceResponse asset(Uri u){
        try{
            if(!isLocal(u))throw new Exception("Non-local request");
            String path=u.getPath().substring(8);
            if(path.contains("..")||path.startsWith("/"))throw new Exception("Invalid path");
            String mime=path.endsWith(".html")?"text/html":path.endsWith(".js")?"application/javascript":path.endsWith(".css")?"text/css":path.endsWith(".svg")?"image/svg+xml":path.endsWith(".png")?"image/png":path.endsWith(".woff")?"font/woff":"text/plain";
            return new WebResourceResponse(mime,"UTF-8",getAssets().open(path));
        }catch(Exception e){return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",null,new ByteArrayInputStream(new byte[0]));}
    }
    public final class LocalBridge {
        @JavascriptInterface public String getState(){return prefs.getString("state","");}
        @JavascriptInterface public boolean setState(String value){
            try{if(value==null||value.length()>2000000||new JSONObject(value).optInt("schema")!=1)return false;return prefs.edit().putString("state",value).commit();}catch(Exception e){return false;}
        }
        @JavascriptInterface public void haptic(){runOnUiThread(new Runnable(){public void run(){web.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);}});}
        @JavascriptInterface public void exportBackup(final String body,final String name){
            if(body==null||body.length()>2000000)return;
            runOnUiThread(new Runnable(){public void run(){
                pendingExport=body;prefs.edit().putString("pendingExport",body).apply();
                Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");i.putExtra(Intent.EXTRA_TITLE,name);
                try{startActivityForResult(i,EXPORT);}catch(Exception e){pendingExport=null;prefs.edit().remove("pendingExport").apply();message("这台设备没有可用的文件保存应用");}
            }});
        }
        @JavascriptInterface public void importBackup(){runOnUiThread(new Runnable(){public void run(){
            Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");i.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/json","text/plain","application/octet-stream"});
            try{startActivityForResult(i,IMPORT);}catch(Exception e){message("这台设备没有可用的文件选择应用");}
        }});}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(result!=RESULT_OK||data==null||data.getData()==null){if(request==EXPORT){pendingExport=null;prefs.edit().remove("pendingExport").apply();}return;}
        try{
            if(request==EXPORT&&pendingExport!=null){
                try(OutputStream stream=getContentResolver().openOutputStream(data.getData(),"wt")){if(stream==null)throw new Exception();stream.write(pendingExport.getBytes(StandardCharsets.UTF_8));}
                pendingExport=null;prefs.edit().remove("pendingExport").apply();message("备份已保存");
            }else if(request==IMPORT){
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                try(InputStream stream=getContentResolver().openInputStream(data.getData())){
                    if(stream==null)throw new Exception();byte[] buf=new byte[4096];int count;
                    while((count=stream.read(buf))!=-1){if(out.size()+count>2000000)throw new Exception("too large");out.write(buf,0,count);}
                }
                final String content=new String(out.toByteArray(),StandardCharsets.UTF_8);
                web.evaluateJavascript("window.acceptImported("+JSONObject.quote(content)+")",null);
            }
        }catch(Exception e){pendingExport=null;prefs.edit().remove("pendingExport").apply();message("文件操作失败，请检查文件格式或存储空间");}
    }
    private void message(String text){Toast.makeText(this,text,Toast.LENGTH_SHORT).show();}
    @Override public void onBackPressed(){web.evaluateJavascript("window.handleBack ? window.handleBack() : false",new ValueCallback<String>(){public void onReceiveValue(String value){if(!"true".equals(value))MainActivity.super.onBackPressed();}});}
    @Override protected void onPause(){super.onPause();web.evaluateJavascript("window.dispatchEvent(new Event('luodi-background'))",null);web.onPause();}
    @Override protected void onResume(){super.onResume();if(web!=null){web.onResume();web.evaluateJavascript("window.dispatchEvent(new Event('focus'))",null);}}
    @Override protected void onDestroy(){if(web!=null){web.removeJavascriptInterface("LuodiNative");web.destroy();}super.onDestroy();}
}
