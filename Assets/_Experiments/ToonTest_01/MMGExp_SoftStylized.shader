// Experiment only (ToonTest_01): soft stylized shading for URP (wrapped diffuse, warm shadow tint, soft specular, rim).
// Light direction and ambient come from material values so the test does not depend on scene lights.
Shader "MMGExp/SoftStylized"
{
    Properties
    {
        _BaseColor ("Base", Color) = (0.99, 0.81, 0.74, 1)
        _ShadowColor ("Shadow tint", Color) = (0.86, 0.55, 0.5, 1)
        _Wrap ("Wrap", Range(0, 1)) = 0.45
        _ShadowPow ("Shadow falloff", Range(0.3, 3)) = 1.2
        _Ambient ("Ambient", Range(0, 1)) = 0.18
        _SpecColor ("Specular", Color) = (1, 0.95, 0.92, 1)
        _SpecPow ("Specular power", Range(1, 256)) = 24
        _SpecStrength ("Specular strength", Range(0, 2)) = 0.12
        _RimColor ("Rim", Color) = (1, 0.92, 0.86, 1)
        _RimPow ("Rim power", Range(0.5, 8)) = 4
        _RimStrength ("Rim strength", Range(0, 1)) = 0.25
        _LightDir ("Light direction (world)", Vector) = (-0.3, 0.8, -0.5, 0)
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }
        Pass
        {
            Name "Soft"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor, _ShadowColor, _SpecColor, _RimColor;
                float _Wrap, _ShadowPow, _Ambient, _SpecPow, _SpecStrength, _RimPow, _RimStrength;
                float4 _LightDir;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct V { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; float3 viewWS : TEXCOORD1; };
            V vert(A i)
            {
                V o;
                VertexPositionInputs p = GetVertexPositionInputs(i.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.viewWS = GetWorldSpaceViewDir(p.positionWS);
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                float3 v = normalize(i.viewWS);
                float3 l = normalize(_LightDir.xyz);
                float wrap = saturate((dot(n, l) + _Wrap) / (1 + _Wrap));
                float shade = pow(wrap, _ShadowPow);
                half3 col = lerp(_BaseColor.rgb * _ShadowColor.rgb, _BaseColor.rgb, shade);
                col = lerp(col, _BaseColor.rgb, _Ambient);
                float spec = pow(saturate(dot(n, normalize(l + v))), _SpecPow) * _SpecStrength;
                float rim = pow(1 - saturate(dot(n, v)), _RimPow) * _RimStrength * (0.4 + 0.6 * wrap);
                col += spec * _SpecColor.rgb + rim * _RimColor.rgb;
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
}
