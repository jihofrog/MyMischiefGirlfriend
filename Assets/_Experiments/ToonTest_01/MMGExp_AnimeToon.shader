// Experiment only (ToonTest_01): stepped toon ramp + inverted-hull outline pass for URP.
// Light direction comes from _LightDir so the test does not depend on scene lights; production would use GetMainLight().
Shader "MMGExp/AnimeToon"
{
    Properties
    {
        _ShadowColor ("Shadow", Color) = (0.93, 0.67, 0.59, 1)
        _MidColor ("Mid", Color) = (0.99, 0.76, 0.69, 1)
        _BaseColor ("Base", Color) = (0.99, 0.81, 0.74, 1)
        _LightColor ("Light", Color) = (1, 0.88, 0.82, 1)
        _T1 ("Shadow edge", Range(0, 1)) = 0.34
        _T2 ("Mid edge", Range(0, 1)) = 0.5
        _T3 ("Light edge", Range(0, 1)) = 0.72
        _Soft ("Edge softness", Range(0.001, 0.2)) = 0.04
        _LightDir ("Light direction (world)", Vector) = (-0.3, 0.8, -0.5, 0)
        _HairBand ("Hair highlight band (0/1)", Float) = 0
        _BandColor ("Band colour", Color) = (0.84, 0.59, 0.54, 1)
        _BandLo ("Band low (normal.y)", Range(-1, 1)) = 0.55
        _BandHi ("Band high (normal.y)", Range(-1, 1)) = 0.8
        _OutlineColor ("Outline", Color) = (0.26, 0.12, 0.1, 1)
        _OutlineWidth ("Outline width (m)", Float) = 0.0011
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            half4 _ShadowColor, _MidColor, _BaseColor, _LightColor, _BandColor, _OutlineColor;
            float _T1, _T2, _T3, _Soft, _HairBand, _BandLo, _BandHi, _OutlineWidth;
            float4 _LightDir;
        CBUFFER_END
        ENDHLSL

        Pass
        {
            Name "Toon"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
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
                float l = saturate(dot(n, normalize(_LightDir.xyz)));
                float a = smoothstep(_T1 - _Soft, _T1 + _Soft, l);
                float b = smoothstep(_T2 - _Soft, _T2 + _Soft, l);
                float c = smoothstep(_T3 - _Soft, _T3 + _Soft, l);
                half3 col = lerp(lerp(lerp(_ShadowColor.rgb, _MidColor.rgb, a), _BaseColor.rgb, b), _LightColor.rgb, c);
                if (_HairBand > 0.5)
                {
                    float band = smoothstep(_BandLo, _BandLo + 0.04, n.y) * (1 - smoothstep(_BandHi - 0.04, _BandHi, n.y));
                    float facing = saturate(dot(n, normalize(i.viewWS)));
                    col = lerp(col, _BandColor.rgb, band * facing);
                }
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct V { float4 positionCS : SV_POSITION; };
            V vert(A i)
            {
                V o;
                float3 ws = TransformObjectToWorld(i.positionOS.xyz) + TransformObjectToWorldNormal(i.normalOS) * _OutlineWidth;
                o.positionCS = TransformWorldToHClip(ws);
                return o;
            }
            half4 frag(V i) : SV_Target { return _OutlineColor; }
            ENDHLSL
        }
    }
}
